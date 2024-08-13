import requests
import os
import sys
import json
import time
from datetime import datetime, timezone
import concurrent.futures
import uuid
from dotenv import load_dotenv

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
RANGE_NAME = os.getenv("RANGE_NAME")


def saveDataToSheet(data):
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)

        sheet = service.spreadsheets()
        body = { 'values': [data] }
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption='RAW',
            body=body
        ).execute()

    except HttpError as err:
        print(err)


def getProcessedVideos():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Sheet1!A:A"
        ).execute()

        values = result.get('values', [])

        processedVideos = []
        for value in values:
            processedVideos.append(value[0])
        return processedVideos
    except HttpError as err:
        print(err)
        return None


def get_vimeo_data(path):
    access_token = os.getenv("ACCESS_TOKEN")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    url = f"https://api.vimeo.com{path}"
    headers = {
        "Authorization": f"bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code >= 500 and response.status_code < 600:
        time.sleep(30)
        response = requests.get(url, headers=headers)

    if response.status_code == 429:
        time.sleep(60)
        response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code}")
    return response.json()

def get_folder_path(folder):
    try:
        parent_path = [folder['name']]
        encoded_path = ""

        # if len(folder['metadata']['connections']['ancestor_path']) > 0:
        #     ancestor_path = folder['metadata']['connections']['ancestor_path'][0]['uri']

        #     while ancestor_path:
        #         folder_info = get_vimeo_data(ancestor_path)
        #         if len(folder_info['metadata']['connections']['ancestor_path']) > 1:
        #             ancestor_path = folder_info['metadata']['connections']['ancestor_path'][0]['uri']
        #             parent_path.append(folder_info['name'])
        #         else:
        #             ancestor_path = None

        for element in reversed(folder['metadata']['connections']['ancestor_path']):
            encoded_path += f"/{requests.utils.quote(element['name'])}"
        encoded_path += f"/{requests.utils.quote(folder['name'])}"
        folder['metadata']['connections']['ancestor_path']
        return encoded_path
    except Exception as e:
        print(f"Error getting folder path: {e}")

def getVimeoVideos():
    try:
        user_id = os.getenv("USER_ID")

        next_page = f"/users/{user_id}/folders?page=1"
        processedVideos = getProcessedVideos()

        def process_video_wrapper(args):
            name, collection, download_link, video_link = args
            if video_link not in processedVideos:
                print(f"URL: {video_link}")
                process_video(name, collection, download_link, video_link)
            # else:
                # print(f"Skipping: {video_link}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            while next_page:
                print(f"Processing folder: {next_page}")
                user_folders = get_vimeo_data(next_page)
                next_page = user_folders['paging']['next']
                folders_data = user_folders['data']

                for user_folder in folders_data:
                    if len(user_folder['metadata']['connections']['ancestor_path']) > 0:
                        collectionName = user_folder['metadata']['connections']['ancestor_path'][-1]["name"]
                    else:
                        collectionName = user_folder["name"]
                    folder_items_next_page = f"{user_folder['uri']}/videos?page=1"

                    while folder_items_next_page:
                        folder_contents = get_vimeo_data(folder_items_next_page)
                        folder_items_next_page = folder_contents['paging']['next']
                        # print(f"Processing: {folder_items_next_page}")
                        folder_data = folder_contents['data']

                        futures = []
                        for folder_content_item in folder_data:
                            download_quality = max(folder_content_item['download'], key=lambda x: int(x['rendition'].replace("p", "")))
                            future = executor.submit(process_video_wrapper, (
                                folder_content_item['name'],
                                collectionName,
                                download_quality['link'],
                                folder_content_item['link']
                            ))
                            futures.append(future)
                        concurrent.futures.wait(futures)
        print("Processed all videos")
    except Exception as e:
        print(f"Error: {e}")

def download_video(output_location_path, url):
    response = requests.get(url, stream=True)
    with open(f"videos/{output_location_path}", "wb") as writer:
        for chunk in response.iter_content(chunk_size=8192):
            writer.write(chunk)


def upload_to_bunny_cdn(fileNameValid, fileName, collectionName, libraryId, access_key):
    try:
        url = f"https://video.bunnycdn.com/library/{libraryId}/collections?page=1&itemsPerPage=10&search={collectionName}&orderBy=date&includeThumbnails=false"

        headers = {
            "accept": "application/json",
            "AccessKey": access_key
        }

        response = requests.request("GET", url, headers=headers)
        data = json.loads(response.text)
        
        collectionId = None
        if data["totalItems"] <= 0:
            url = f"https://video.bunnycdn.com/library/{libraryId}/collections"
            payload = { "name": collectionName }
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "AccessKey": access_key
            }
            response = requests.request("POST", url, json = payload, headers = headers)
            data = json.loads(response.text)
            collectionId = data["guid"]
        else:
            collectionId = data["items"][0]["guid"]

        url = f"https://video.bunnycdn.com/library/{libraryId}/videos"
        video_path = f"videos/{fileNameValid}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "AccessKey": access_key
        }

        payload = json.dumps({ "title": fileName, "collectionId": collectionId })
        
        response = requests.request("POST", url, headers=headers, data=payload)
        data = json.loads(response.text)

        videoId = data["guid"]

        url = f"https://video.bunnycdn.com/library/{libraryId}/videos/{videoId}"

        with open(video_path, 'rb') as f:
            headers = {
                'Content-Type': 'application/octet-stream',
                'AccessKey': access_key,
            }
            response = requests.request("PUT", url, headers=headers, data=f)
            data = json.loads(response.text)
            if data["statusCode"] == 200:
                videoUrl = f"https://iframe.mediadelivery.net/play/{libraryId}/{videoId}"
                return videoUrl
            else:
                return None
    except Exception as e:
        print(f"Upload error: {e}")
        return None

def save_data(new_data):
    try:
        if os.path.exists("UrlMapping.json"):
            with open("UrlMapping.json", "r", encoding="utf8") as f:
                data = json.load(f)
        else:
            data = []

        data.append(new_data)

        with open("UrlMapping.json", "w", encoding="utf8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error handling the file: {e}")

def process_video(video_name, collectionName, video_link, vimeo_file_url):
    try:
        bunny_api_key = "89d81f13-6ff0-4186-96410d9b7a5e-5dca-4ff9"
        library_id = "262708"
        file_name = f"{video_name}.mp4"
        fileNameValid = str(uuid.uuid4()) + ".mp4"
        download_video(fileNameValid, video_link)

        file_path = f"videos/{fileNameValid}"

        response = upload_to_bunny_cdn(fileNameValid, file_name, collectionName, library_id, bunny_api_key)
        bunny_file_url = None
        if response is not None:
            bunny_file_url = response
            print(f"File: {bunny_file_url}")
        else:
            print("Error uploading")

        current_utc_time = datetime.now(timezone.utc)
        saveDataToSheet([vimeo_file_url, bunny_file_url, str(current_utc_time)])
        os.remove(file_path)
    except Exception as e:
        print(f"Error: {e}")

getVimeoVideos()
