const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const FFMPEG_URL = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip';
const DOWNLOAD_PATH = path.join(__dirname, 'ffmpeg.zip');
const EXTRACT_PATH = path.join(__dirname, 'ffmpeg');

console.log('Downloading FFmpeg...');

// Download FFmpeg
const file = fs.createWriteStream(DOWNLOAD_PATH);
https.get(FFMPEG_URL, (response) => {
    response.pipe(file);
    file.on('finish', () => {
        file.close();
        console.log('Download completed. Extracting...');

        // Create ffmpeg directory if it doesn't exist
        if (!fs.existsSync(EXTRACT_PATH)) {
            fs.mkdirSync(EXTRACT_PATH, { recursive: true });
        }

        // Extract using PowerShell (built into Windows)
        try {
            execSync(`powershell -command "Expand-Archive -Path '${DOWNLOAD_PATH}' -DestinationPath '${EXTRACT_PATH}' -Force"`, { stdio: 'inherit' });
            console.log('Extraction completed.');

            // Clean up zip file
            fs.unlinkSync(DOWNLOAD_PATH);
            console.log('Cleaned up temporary files.');
            console.log('FFmpeg setup completed successfully!');
        } catch (err) {
            console.error('Error during extraction:', err);
        }
    });
}).on('error', (err) => {
    console.error('Error downloading FFmpeg:', err);
    fs.unlinkSync(DOWNLOAD_PATH);
});
