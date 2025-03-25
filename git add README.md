# Panorama Studio

A web-based tool for creating 360° panoramas using Flask and OpenCV. Supports two modes: real-time stitching as you capture images, or capturing up to 20 images first and stitching later.

## Features
- Capture images at 18° increments for a full 360° horizontal panorama.
- Real-time stitching mode shows the panorama as you go.
- Capture-first mode stitches all images at once when complete.
- Self-signed SSL for secure local testing.
- Built with Flask, OpenCV, and a Tailwind CSS frontend.

## Prerequisites
- Python 3.8+
- Git

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/Panorama-Studio.git
   cd Panorama-Studio