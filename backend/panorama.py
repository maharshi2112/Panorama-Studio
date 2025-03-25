from flask import Flask, Response, jsonify, request
import cv2
import numpy as np
from datetime import datetime
import base64
import ssl
import os
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import datetime as dt

app = Flask(__name__)

class PanoramaCreator:
    def __init__(self):
        self.images = []
        self.max_images = 20
        self.target_angle_increment = 18
        self.current_pano = None
        self.stitcher = cv2.Stitcher_create()
        self.mode = "previous"  # Default to previous mode

    def set_mode(self, mode):
        self.mode = mode if mode in ["realtime", "previous"] else "previous"
        if self.mode == "previous":
            self.current_pano = None  # Reset live panorama in previous mode

    def add_image(self, image_data):
        try:
            nparr = np.frombuffer(base64.b64decode(image_data.split(',')[1]), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            img = cv2.resize(img, (640, 480))
            if len(self.images) < self.max_images:
                self.images.append(img)
                if self.mode == "realtime" and len(self.images) >= 2:
                    if self.current_pano is None:
                        status, self.current_pano = self.stitcher.stitch(self.images[:2])
                    else:
                        status, self.current_pano = self.stitcher.stitch([self.current_pano, img])
                    if status != cv2.Stitcher_OK:
                        print(f"Incremental stitching failed with status: {status}")
                        self.current_pano = None
                        return False
                return True
            return False
        except Exception as e:
            print(f"Error decoding image: {e}")
            return False

    def get_current_panorama(self):
        if self.current_pano is not None:
            _, buffer = cv2.imencode('.jpg', self.current_pano)
            return base64.b64encode(buffer).decode('utf-8')
        return None

    def create_panorama(self):
        if len(self.images) < 2:
            return None

        if self.mode == "realtime" and self.current_pano is not None:
            # Use the existing real-time panorama
            pano = self.current_pano
        else:
            # Stitch all images at once (previous mode)
            status, pano = self.stitcher.stitch(self.images)
            if status != cv2.Stitcher_OK:
                print(f"Stitching failed with status: {status}")
                return None

        # Save the panorama
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"static/panorama_{timestamp}.jpg"
        cv2.imwrite(filename, pano)
        return filename

    def get_status(self):
        return {
            "image_count": len(self.images),
            "next_angle": len(self.images) * self.target_angle_increment if len(self.images) < self.max_images else "Complete",
            "mode": self.mode
        }

    def reset(self):
        self.images = []
        self.current_pano = None

pano_creator = PanoramaCreator()

def generate_self_signed_cert():
    if not os.path.exists('cert.pem') or not os.path.exists('key.pem'):
        print("Generating self-signed certificate...")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"YourState"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"YourCity"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"PanoramaApp"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"192.168.0.103"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(dt.datetime.utcnow())
            .not_valid_after(dt.datetime.utcnow() + dt.timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(u"192.168.0.103")]), critical=False)
            .sign(private_key, hashes.SHA256())
        )
        with open("key.pem", "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        with open("cert.pem", "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        print("Generated key.pem and cert.pem successfully!")
    else:
        print("Using existing cert.pem and key.pem.")

@app.route('/')
def index():
    print("Serving index.html")
    return app.send_static_file('index.html')

@app.route('/set_mode', methods=['POST'])
def set_mode():
    data = request.json
    mode = data.get('mode')
    pano_creator.set_mode(mode)
    return jsonify({"success": True, "mode": pano_creator.mode})

@app.route('/capture', methods=['POST'])
def capture():
    print("Received /capture request")
    data = request.json
    image_data = data.get('image')
    success = pano_creator.add_image(image_data)
    pano_data = pano_creator.get_current_panorama()
    return jsonify({
        "success": success,
        "pano_data": pano_data,
        **pano_creator.get_status()
    })

@app.route('/stitch', methods=['POST'])
def stitch():
    print("Received /stitch request")
    panorama_path = pano_creator.create_panorama()
    if panorama_path:
        pano_creator.reset()
        return jsonify({"success": True, "panorama_url": f"/{panorama_path}"})
    return jsonify({"success": False, "error": "Stitching failed"})

@app.route('/status')
def status():
    print("Received /status request")
    pano_data = pano_creator.get_current_panorama()
    return jsonify({
        **pano_creator.get_status(),
        "pano_data": pano_data
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=context)
