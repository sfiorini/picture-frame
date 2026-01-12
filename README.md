# Picture Frame

A web-based photo slideshow application optimized for Safari on iOS 5.1.1 (iPad 1st gen). Displays photos from local folders with configurable timing, fade transitions, and simple API key authentication.

## Features

- **iOS 5.1.1 Compatible**: ES5 JavaScript and CSS3 transitions work on older Safari
- **HEIC Support**: Automatic server-side transcoding of HEIC photos to JPEG
- **Blurred Background**: Photos display with a blurred background layer that fills black bands from aspect ratio mismatches
- **Smart Positioning**: Automatically adjusts image positioning based on device and photo orientation (landscape/portrait)
- **Multiple Photo Directories**: Configure one or more local folders
- **Configurable Display**: Adjust delay, fade duration, and display order (random/sequential)
- **Simple Authentication**: API key authentication via query parameter or header
- **Docker Deployment**: Easy deployment with Docker Compose

## Quick Start

### 1. Generate an API Key

Generate a secure API key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update with your settings:

```bash
cp .env.example .env
```

Edit `.env` and set your API key:

```bash
API_KEY=your-generated-api-key-here
```

### 3. Add Photos

Create a `photos` directory and add your photos:

```bash
mkdir photos
cp /path/to/your/photos/* photos/
```

### 4. Run with Docker Compose

```bash
docker-compose up -d
```

The application will be available at `http://localhost:5000`

### 5. Access from iPad

Open Safari on your iPad and navigate to:

```
http://your-server-ip:5000/?api_key=your-api-key-here
```

**For the best experience**, add the page to your home screen:
1. Tap the Share/Action button in Safari
2. Tap "Add to Home Screen"
3. Launch from the home screen icon

Note: On iOS 5.1.1, the system status bar (time, battery) will always be visible at the top, even in home screen mode. The layout is adjusted to account for this.

## Configuration

Configuration is done via environment variables in `.env` or `docker-compose.yml`:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Authentication key (required) | - |
| `PHOTO_DIRS` | Comma-separated list of photo directories | `/photos` |
| `PHOTO_DELAY_SECONDS` | Delay between photos (seconds) | `10` |
| `DISPLAY_ORDER` | Photo order: `random` or `sequential` | `random` |
| `FADE_DURATION_MS` | Fade transition duration (milliseconds) | `1000` |
| `ENABLE_CACHE` | Enable HEIC transcoding cache | `true` |
| `SECRET_KEY` | Flask secret key | auto-generated |
| `DEBUG` | Enable debug mode | `false` |

### Multiple Photo Directories

To use multiple photo directories, separate them with commas:

```bash
PHOTO_DIRS=/photos,/mnt/external-photos,/path/to/more/photos
```

Then update the volume mounts in `docker-compose.yml`:

```yaml
volumes:
  - ./photos:/photos:ro
  - /mnt/external-photos:/mnt/external-photos:ro
  - /path/to/more/photos:/path/to/more/photos:ro
```

## API Endpoints

### `GET /`
Main slideshow page (H5 HTML5 page)

### `GET /api/config`
Get client configuration (no authentication required)

Returns:
```json
{
  "delay": 10000,
  "fadeDuration": 1000,
  "displayOrder": "random"
}
```

### `GET /api/photos`
List all available photos (requires authentication)

Query parameters:
- `api_key`: Your API key
- `order`: `random` or `sequential`

Returns:
```json
{
  "photos": [
    {
      "id": "photo_abc123",
      "name": "photo",
      "is_heic": false,
      "url": "/api/photo/abc123"
    }
  ],
  "count": 1
}
```

### `GET /api/photo/<photo_id>`
Serve a single photo (handles HEIC transcoding and blur generation)

Query parameters:
- `api_key`: Your API key
- `blur`: Set to `true` to get a blurred version for background display

The blurred version is:
- Downscaled to max 800px dimension
- Heavily blurred using Gaussian blur (radius 30)
- Saved as JPEG with 70% quality
- Cached for 24 hours (vs 1 hour for normal photos)

### `GET /health`
Health check endpoint for container monitoring

## Authentication

The API key can be provided in two ways:

1. **Query Parameter**: `?api_key=your-key`
2. **Request Header**: `X-API-Key: your-key`

Once authenticated via the URL parameter, the key is saved to localStorage for subsequent requests.

## Supported Photo Formats

- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- HEIC (`.heic`, `.heif`) - automatically transcoded to JPEG

## Display Behavior

### Blurred Background Layer

Every photo displays with a blurred version of itself as a background layer. This eliminates black bars and creates a polished visual experience:

- **Server-side blur generation**: Images are downscaled (max 800px) and heavily blurred (Gaussian blur) on the server for performance
- **Full-screen stretched background**: The blurred image is stretched via JavaScript to exactly fill the viewport (required for iOS 5.1.1 compatibility)
- **Sharp foreground**: The actual photo is positioned on top using smart positioning logic
- **Natural fill**: Where the sharp image doesn't fill the screen, the blurred background shows through

### Smart Image Positioning

The application automatically positions the sharp foreground photo based on device and photo orientation:

| Device | Photo | Behavior |
|--------|-------|----------|
| Landscape | Portrait | Fill height, crop sides |
| Portrait | Landscape | Fill width, crop top/bottom |
| Matching | Same orientation | Fill based on aspect ratio comparison |

## Development

### Running Locally

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set environment variables:

```bash
export API_KEY=dev-key
export PHOTO_DIRS=./photos
```

4. Run the application:

```bash
flask --app app run
```

### Running Tests

```bash
pytest
```

## Docker Deployment

### Build Only

```bash
docker build -t picture-frame .
```

### Build and Run

```bash
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f
```

### Stop

```bash
docker-compose down
```

## Troubleshooting

### Photos not showing

1. Check that photo directories are correctly mounted
2. Verify API key is correct
3. Check container logs: `docker-compose logs`

### HEIC photos not displaying

1. Ensure HEIC support is enabled (check logs for pillow-heif errors)
2. Verify cache directory is writable
3. Check that the HEIC file is not corrupted

### iPad can't connect

1. Ensure iPad and server are on the same network
2. Check firewall settings on the server
3. Verify the server IP address is correct
4. Try accessing from another device first

#### WSL2 (Windows) Networking

If running Docker Desktop on WSL2, external devices may not be able to access the container. Set up Windows port forwarding:

```powershell
# Get WSL2 IP
wsl hostname -I

# Add port forwarding (replace WSL_IP with actual IP)
netsh interface portproxy add v4tov4 listenport=5000 listenaddress=0.0.0.0 connectport=5000 connectaddress=WSL_IP

# View existing rules
netsh interface portproxy show all

# Remove rule when done
netsh interface portproxy delete v4tov4 listenport=5000 listenaddress=0.0.0.0
```

## License

MIT

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
