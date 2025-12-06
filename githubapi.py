import requests
import base64
import json
import os
import random
from getpass import getpass

class GitHubAPI:
    def __init__(self, username, repository, token):
        self.username = username
        self.repository = repository
        self.base_url = f"https://api.github.com/repos/{username}/{repository}/contents/"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def _get_sha(self, targetfile):
        url = self.base_url + targetfile
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json().get('sha')
        return None

    
    def get_file(self, targetfile, local_path=None):
        url = self.base_url + targetfile
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('type') == 'file':
                content_base64 = data.get('content', '')
                content = base64.b64decode(content_base64)
                
                if local_path:
                    try:
                        
                        with open(local_path, 'wb') as f:
                            f.write(content)
                        return f"Success: File saved to {local_path}"
                    except Exception as e:
                        return f"Error: Failed to save file locally: {e}"
                
                
                return content.decode('utf-8')

            return f"Error: {targetfile} is not a file."
        elif response.status_code == 404:
            return f"Error: {targetfile} not found (404)."
        return f"Error: Failed to fetch file. Status Code: {response.status_code}"

    def set_file(self, targetfile, content, commit_message="File updated/created."):
        url = self.base_url + targetfile
        
        sha = self._get_sha(targetfile)

        if isinstance(content, str):
            content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        elif isinstance(content, bytes):
             content_base64 = base64.b64encode(content).decode('utf-8')
        else:
             return "Error: Content must be string or bytes.", None

        payload = {
            "message": commit_message,
            "content": content_base64
        }
        
        if sha:
            payload["sha"] = sha

        response = requests.put(url, headers=self.headers, data=json.dumps(payload))
        
        if response.status_code in [200, 201]:
            return "Success", response.json()
        return f"Error: Failed operation. Status Code: {response.status_code} - {response.json().get('message', 'Unknown Error')}", None

    def del_file(self, targetfile, commit_message="File deleted."):
        url = self.base_url + targetfile
        
        sha = self._get_sha(targetfile)
        
        if not sha:
            return f"Error: {targetfile} not found or SHA not retrieved.", None

        payload = {
            "message": commit_message,
            "sha": sha
        }

        response = requests.delete(url, headers=self.headers, data=json.dumps(payload))

        if response.status_code == 200:
            return "Success", response.json()
        return f"Error: Failed to delete file. Status Code: {response.status_code} - {response.json().get('message', 'Unknown Error')}", None

    def list_dir(self, targetdir=""):
        url = self.base_url + targetdir
        
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            contents = response.json()
            if isinstance(contents, list):
                return [{"name": item['name'], "type": item['type']} for item in contents]
            return f"Error: {targetdir} is not a directory."
        elif response.status_code == 404:
            return f"Error: Directory {targetdir} not found (404)."
        return f"Error: Directory listing failed. Status Code: {response.status_code}"

    def create_dir(self, targetdir):
        file_path = f"{targetdir.rstrip('/')}/.gitkeep"
        content = " " 
        commit_message = f"Directory created: {targetdir}"
        
        result, data = self.set_file(file_path, content, commit_message)
        
        if "Success" in result and data and data.get('content', {}).get('type') == 'file':
            return "Success", data
        return f"Error: Directory creation failed: {result}", data
            
    def del_dir(self, targetdir, commit_message="Directory deleted."):
        file_path = f"{targetdir.rstrip('/')}/.gitkeep"
        
        result, data = self.del_file(file_path, commit_message)
        
        if "Success" in result:
            return "Success", data
        elif "not found" in result:
             return f"Info: .gitkeep in {targetdir} not found. Directory might be empty.", data
        return f"Error: Directory deletion failed: {result}", data

    def is_file(self, targetpath):
        url = self.base_url + targetpath
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return 'dir'
            return data.get('type')
        return None

    
    def move_file(self, old_path, new_path, commit_message="File moved."):
        
        url_old = self.base_url + old_path
        response_old = requests.get(url_old, headers=self.headers)
        
        if response_old.status_code != 200:
            return f"Error: Failed to fetch old file content. Status Code: {response_old.status_code}", None
        
        data_old = response_old.json()
        if data_old.get('type') != 'file':
            return f"Error: {old_path} is not a file.", None
        
        content_base64 = data_old.get('content', '')
        content_bytes = base64.b64decode(content_base64)
        
        
        new_commit_message = f"Move: {old_path} -> {new_path}" if commit_message == "File moved." else commit_message
        status_set, data_set = self.set_file(new_path, content_bytes, new_commit_message)
        
        if "Success" not in status_set:
            return f"Error: Failed to create file at new path: {status_set}", data_set
            
        
        status_del, data_del = self.del_file(old_path, new_commit_message)
        
        if "Success" not in status_del:
        
            return f"Warning: File created at {new_path}, but failed to delete old file {old_path}. Delete manually. Error: {status_del}", data_set
        
        return f"Success: File moved from {old_path} to {new_path}", data_set


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main_menu():
    print("\n=== GitHub Repository Manager ===")
    print("1. List Directory")
    print("2. Read/Download File")
    print("3. Upload/Edit File (from local file)")
    print("4. Delete File")
    print("5. Create Directory")
    print("6. Delete Directory")
    print("7. Move/Rename File")
    print("8. Active Ping")
    print("9. Exit") 
    print("-" * 40)
    return input("Choose an option (1-9): ").strip()

def main():
    clear_screen()
    print("=== GitHub Repo Manager ===")
    print("Generate a Personal Access Token: https://github.com/settings/tokens")
    print("(Required scope: repo)\n")

    username = input("GitHub Username: ").strip()
    repository = input("Repository Name: ").strip()
    token = getpass("Personal Access Token (hidden): ").strip()

    if not all([username, repository, token]):
        print("All fields are required!")
        return

    api = GitHubAPI(username, repository, token)

    
    print("\nTesting connection...")
    test = api.list_dir("")
    if isinstance(test, str) and "Error" in test:
        print(f"Connection failed: {test}")
        print("Check your token, permissions, username, or repository name.")
        return
    else:
        print(f"Successfully connected to {username}/{repository}\n")
        input("Press Enter to continue...")

    while True:
        clear_screen()
        print(f"=== {username}/{repository} ===")
        choice = main_menu()

        if choice == "1":
            path = input("\nPath (leave empty for root): ").strip() or ""
            result = api.list_dir(path)
            print("\nContents:")
            if isinstance(result, list):
                for item in result:
                    icon = "DIR" if item['type'] == 'dir' else "FILE"
                    print(f" [{icon}] {item['name']}")
            else:
                print(result)
            input("\nPress Enter to continue...")

        elif choice == "2":
            path = input("\nFile path to read/download: ").strip()
            
            local_path = input("Local path to save (optional, leave empty to display): ").strip() or None
            
            content = api.get_file(path, local_path)
            
            print("\n" + "="*60)
            if local_path and "Success" in content:
                 print(content)
            elif "Error" not in content:
                print(content)
            else:
                print(content)
            print("="*60)
            input("\nPress Enter to continue...")

        elif choice == "3":
            repo_path = input("\nTarget path in repo (e.g. folder/script.py): ").strip()
            local_path = input("Local file path (source): ").strip()

            if not os.path.isfile(local_path):
                print("Local file not found!")
                input("Press Enter to continue...")
                continue

            with open(local_path, 'rb') as f: # Dosyayı ikili (binary) olarak oku
                content = f.read()

            message = input("Commit message (empty = default): ").strip()
            if not message:
                message = f"Update {os.path.basename(local_path)}"

            print("Uploading...")
            status, _ = api.set_file(repo_path, content, message)
            print(status)
            input("Press Enter to continue...")

        elif choice == "4":
            path = input("\nFile path to delete: ").strip()
            msg = input("Commit message (empty = default): ").strip() or "File deleted"
            status, _ = api.del_file(path, msg)
            print(status)
            input("Press Enter to continue...")

        elif choice == "5":
            path = input("\nDirectory to create (e.g. new-folder/subfolder): ").strip()
            status, _ = api.create_dir(path)
            print(status)
            input("Press Enter to continue...")

        elif choice == "6":
            path = input("\nDirectory to delete (must be empty or contain only .gitkeep): ").strip()
            msg = input("Commit message (empty = default): ").strip() or "Directory deleted"
            status, _ = api.del_dir(path, msg)
            print(status)
            input("Press Enter to continue...")

        elif choice == "7": 
            old_path = input("\nOld file path (source): ").strip()
            new_path = input("New file path (target): ").strip()
            msg = input("Commit message (empty = default): ").strip() or "File moved"
            status, _ = api.move_file(old_path, new_path, msg)
            print(status)
            input("\nPress Enter to continue...")
        
        elif choice == "8":
        	count = int(input("Activation ping count (use max 2, dont harm github api. just use 1-2 ping for activation): "))
        	for _ in range(count):
        	    name = "."+str(random.randint(0, 1000))+".ping"
        	    api.set_file(name, str(random.random()), "Activate Ping. (Ignore this, just a repo board activation)")
        	    api.del_file(name)
        	input("Press Enter to continue...")
        
        elif choice == "9": 
            print("Goodbye!")
            break

        else:
            print("Invalid option!")
            input("Press Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"Unexpected error: {e}")
        input("Press Enter to exit...") 
