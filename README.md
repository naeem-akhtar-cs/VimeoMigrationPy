# Vimeo to Bunny CDN Video Transfer Tool

## What This Tool Does

This tool helps you automatically transfer your videos from Vimeo to Bunny CDN. It's designed to make the process of moving your video content between these platforms as smooth as possible.

## Key Features

1. **Automatic Video Transfer**: The tool goes through all your Vimeo folders and transfers each video to Bunny CDN.

2. **Keeps Track of Progress**: It remembers which videos have already been transferred, so it doesn't duplicate work.

3. **Organizes Videos**: Your videos will be organized in Bunny CDN using the same folder structure you have in Vimeo.

4. **Records Transfer Details**: After each transfer, it records information like the original Vimeo URL and the new Bunny CDN URL in a Google Spreadsheet.

## What You Need Before Starting

- Vimeo account with videos you want to transfer
- Bunny CDN account
- Google account (for storing transfer records in a Google Spreadsheet)
- Some specific information like API keys and account IDs (your tech team can help set this up)

## How It Works (in Simple Terms)

1. The tool logs into your Vimeo account and looks at all your videos.
2. For each video, it:
   - Downloads the video from Vimeo
   - Uploads the video to Bunny CDN
   - Records the transfer in a Google Spreadsheet
   - Deletes the downloaded file to save space
3. It repeats this process until all videos are transferred.

## Important Notes

- This process can take a long time if you have many videos.
- Make sure you have enough storage space on the computer running this tool.
- The tool is designed to handle interruptions - if it stops, you can restart it and it will pick up where it left off.

## Getting Help

If you encounter any issues or have questions, please contact your technical support team. They can help you set up the necessary accounts, provide the required information, and troubleshoot any problems.
