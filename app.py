# app.py
from flask import Flask, request, send_file, jsonify, render_template
from io import BytesIO
import qrcode
from PIL import Image
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

app = Flask(__name__)

# --- CONFIG (use environment variables) ---
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dzfuo6tvi").strip(),
    api_key=os.getenv("CLOUDINARY_API_KEY", "482262749112535"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "ynABsRmI46AgQvLvGiW_0D5_BTU"),
    secure=True
)

# Serve the main page
@app.route("/")
def index():
    return render_template("index.html")

# Helper: Upload file to Cloudinary and get public URL
def upload_file_to_cloudinary(file, folder="qr_media"):
    try:
        # Determine resource type based on file content type
        resource_type = "auto"
        if file.content_type.startswith('image/'):
            resource_type = "image"
        elif file.content_type.startswith('video/'):
            resource_type = "video"
        elif file.content_type.startswith('audio/'):
            resource_type = "video"  # Cloudinary uses "video" for audio files
        
        # Upload the original file to Cloudinary
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type=resource_type,
            public_id=file.filename.split('.')[0],  # Use filename without extension
            access_mode="public"
        )
        return result.get("secure_url")
    except Exception as e:
        print(f"Cloudinary file upload error: {e}")
        return None

# Helper: Generate QR code image
def generate_qr_image(text, qr_size=400):
    qr = qrcode.QRCode(
        version=1, 
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10, 
        border=4
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    # Resize to desired size
    img = img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
    return img

# Main endpoint for file upload and QR generation
@app.route("/generate_qr", methods=["POST"])
def generate_qr_from_file():
    """
    Endpoint that handles file upload, generates pure QR code with direct media URL
    """
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"})

        # Validate file size (16MB)
        if file.content_length > 16 * 1024 * 1024:
            return jsonify({"success": False, "error": "File size must be less than 16MB"})

        # 1. Upload the original file to Cloudinary to get a public URL
        file_url = upload_file_to_cloudinary(file)
        if not file_url:
            return jsonify({"success": False, "error": "Failed to upload file to cloud storage"})

        # 2. Generate PURE QR code containing the DIRECT MEDIA URL (no background photo)
        qr_img = generate_qr_image(file_url, qr_size=400)

        # 3. Convert QR code to bytes for response
        out_io = BytesIO()
        qr_img.save(out_io, format="PNG")
        out_io.seek(0)

        # 4. Return as base64 for frontend display
        img_base64 = base64.b64encode(out_io.getvalue()).decode('utf-8')
        
        return jsonify({
            "success": True, 
            "qr_image": f"data:image/png;base64,{img_base64}",
            "file_url": file_url,  # The direct media URL
            "filename": file.filename,
            "content_type": file.content_type,
            "qr_content": file_url  # What the QR code actually contains
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# Endpoint to download the pure QR code
@app.route("/download_qr")
def download_qr():
    file_url = request.args.get('url')
    if file_url:
        # Generate QR code for download
        qr_img = generate_qr_image(file_url, qr_size=400)
        out_io = BytesIO()
        qr_img.save(out_io, format="PNG")
        out_io.seek(0)
        
        return send_file(
            out_io,
            mimetype="image/png",
            as_attachment=True,
            download_name="qrcode.png"
        )
    return "No URL provided"

if __name__ == "__main__":
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Move index.html to templates directory if it exists in root
    if os.path.exists('index.html') and not os.path.exists('templates/index.html'):
        os.rename('index.html', 'templates/index.html')
    
    app.run(debug=True, port=5000)