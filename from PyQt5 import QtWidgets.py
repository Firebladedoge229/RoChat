import os
import json
import asyncio
import requests
import configparser
import tkinter as tk
from io import BytesIO
from urllib.request import urlopen

from roblox import Client

client = Client()

async def getUserFromUserId(id):
    user = await client.get_user(id)
    return user.display_name

class ChatApp:
    def __init__(self):
        # Read config file to get cookie
        config = configparser.ConfigParser()
        config.read("config.ini")
        self.roblosecurity_cookie = config.get("CONFIG", ".ROBLOSECURITY")


        # Set up the main window
        self.root = tk.Tk()
        self.previous_len = 0
        self.root.geometry("821x402")
        self.root.title("RoChat")

        response = urlopen("https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Internet_Explorer_10%2B11_logo.svg/1200px-Internet_Explorer_10%2B11_logo.svg.png")
        image_data = response.read()
        photo = tk.PhotoImage(data=image_data)
        self.root.iconphoto(False, photo)

        self.root.minsize(821, 402)
        self.root.maxsize(821, 402)

        self.root.overrideredirect(1)
        self.root.geometry("+0+0")
        self.root.lift()
        self.root.configure(borderwidth=0, highlightthickness=0)
        self.root.overrideredirect(False)

        # Set up the conversation list
        self.conversation_list = tk.Listbox(self.root, width=30, fg="white", bg="#1e2124", borderwidth=0, highlightthickness=0)
        self.conversation_list.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.conversation_list.bind("<<ListboxSelect>>", self.load_chat_history)

        # Set up the chat history box
        self.chat_history = tk.Text(self.root, state=tk.DISABLED, fg="white", bg="#282b30", borderwidth=0, highlightthickness=0)
        self.chat_history.grid(row=0, column=1, sticky="nsew")

        # Set up the message input box
        self.message_input = tk.Entry(self.root, fg="white", bg="#36393e", borderwidth=0, highlightthickness=0)
        self.message_input.grid(row=1, column=1, sticky="we")
        self.message_input.bind("<Return>", self.send_message)
        self.message_input.bind("<Key>", self.on_keypress)

        # Configure grid weights
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)
        self.root.rowconfigure(2, weight=0)
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=2)

        # Ensure conversation list touches the bottom of the window
        self.root.grid_rowconfigure(2, weight=1)

        # Set up the API headers
        self.headers = {
            "Content-Type": "application/json",
            "cookie": f".ROBLOSECURITY={self.roblosecurity_cookie}",
            "x-csrf-token": "cG3sXEh/+Rg6",
        }

        # Fetch the conversations from the API
        self.conversations = self.fetch_conversations()

        # Add the conversations to the list
        for conversation in self.conversations:
            self.conversation_list.insert(tk.END, conversation["title"])

        # Set the selected conversation to the first one
        self.selected_conversation_id = self.conversations[0]["id"]

        # Load the chat history for the first conversation
        self.load_chat_history()

        # Start the main event loop
        self.root.mainloop()

    def on_keypress(self, event):
        current_len = len(self.message_input.get())
        if self.previous_len > 0 and current_len == 0:
            self.update_typing_status(False)
        elif self.previous_len == 0 and current_len > 0:
            self.update_typing_status(True)
        self.previous_len = current_len

    def fetch_conversations(self):
        url = "https://chat.roblox.com/v2/get-user-conversations?pageNumber=1&pageSize=30"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = json.loads(response.text)
            if data:
                return data
        else:
            return []


    def send_message(self, event=None):
        # Get the message from the input box
        message = self.message_input.get()
        self.message_input.delete(0, tk.END)

        # Send the message to the selected conversation
        url = "https://chat.roblox.com/v2/send-message"
        payload = {"conversationId": self.selected_conversation_id, "message": message}

        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 401:  # Authentication failed
            # Update headers with the x-csrf-token
            self.headers['x-csrf-token'] = response.headers.get('x-csrf-token')
            # Make the request again with the updated headers
            response = requests.post(url, headers=self.headers, json=payload)

        if response.status_code == 200:
            # Append the sent message to the chat history box
            self.chat_history.config(state=tk.NORMAL)
            self.chat_history.see(tk.END)
            self.chat_history.config(state=tk.DISABLED)

        # Update the typing status for the selected conversation
        self.load_chat_history()
        self.update_typing_status(False)

    def load_chat_history(self, event=None):
            # Get the selected conversation from the list
            selection = self.conversation_list.curselection()
            if len(selection) == 0:
                return
            selected_conversation = self.conversations[selection[0]]

            # Set the selected conversation ID
            self.selected_conversation_id = selected_conversation["id"]

            # Clear the chat history box
            self.chat_history.config(state=tk.NORMAL)
            self.chat_history.delete("1.0", tk.END)


            # Fetch the chat history for the selected conversation
            url = f"https://chat.roblox.com/v2/get-messages?conversationId={self.selected_conversation_id}&pageSize=100"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                try:
                    data = json.loads(response.text)
                    for message in reversed(data):
                        if message["senderType"] == "User":
                            self.chat_history.insert(
                                tk.INSERT,
                                f"{asyncio.get_event_loop().run_until_complete(getUserFromUserId(message['senderTargetId']))}: {message['content']}\n"
                            )
                        else:
                            self.chat_history.insert(
                                tk.INSERT,
                                f"{asyncio.get_event_loop().run_until_complete(getUserFromUserId(message['senderTargetId']))}: {message['content']}\n"
                            )
                        self.chat_history.see(tk.END)
                except ValueError as e:
                    print(f"Error: {e}")
            else:
                print(f"Error {response.status_code}: {response.reason}")
                # Apply the x-csrf-token mechanism
                if response.status_code == 403:
                    csrf_token = response.headers["x-csrf-token"]
                    self.headers["x-csrf-token"] = csrf_token
                    self.load_chat_history()


            # Update the typing status for the selected conversation
            self.update_typing_status(True)


    def update_typing_status(self, is_typing):
        url = "https://chat.roblox.com/v2/update-user-typing-status"
        headers = {
            "cookie": f".ROBLOSECURITY={self.roblosecurity_cookie}",
            "x-csrf-token": self.headers["x-csrf-token"],  # use the stored CSRF token
            "Content-Type": "application/json"
        }
        data = {
            "conversationId": self.selected_conversation_id,
            "isTyping": is_typing
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            print("Typing status updated successfully.")
        elif response.status_code == 403:
            # update the CSRF token and retry the request
            csrf_token = response.headers["x-csrf-token"]
            self.headers["x-csrf-token"] = csrf_token
            self.update_typing_status(is_typing)  # recursively retry the request
        else:
            print("Failed to update typing status.")

app = ChatApp()