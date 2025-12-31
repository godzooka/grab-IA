# grab-IA Docker Guide

## Quick Start (Headless CLI)

### Build the image
```bash
docker build -t grab-ia:latest .
```

### Run a download job
```bash
# Create directories for volumes
mkdir -p downloads items

# Put your item list in items/items.txt
echo "item_identifier_1" > items/items.txt
echo "item_identifier_2" >> items/items.txt

# Run the container
docker run -it --rm \
  -v $(pwd)/downloads:/downloads \
  -v $(pwd)/items:/items \
  grab-ia:latest \
  start --items /items/items.txt --output /downloads --workers 8
```

## Using Docker Compose

### Headless mode (recommended for servers)
```bash
# Start the service
docker-compose up -d grab-ia-cli

# View logs
docker-compose logs -f grab-ia-cli

# Stop the service
docker-compose down
```

### GUI mode (requires X11 forwarding)
```bash
# Allow X11 connections (Linux only)
xhost +local:docker

# Start GUI service
docker-compose --profile gui up grab-ia-gui

# Revoke X11 access when done
xhost -local:docker
```

## Common Use Cases

### 1. Resume an existing job
```bash
docker run -it --rm \
  -v $(pwd)/downloads:/downloads \
  grab-ia:latest \
  resume --output /downloads --workers 16
```

### 2. Check job status
```bash
docker run -it --rm \
  -v $(pwd)/downloads:/downloads \
  grab-ia:latest \
  status --output /downloads
```

### 3. Download with filters
```bash
docker run -it --rm \
  -v $(pwd)/downloads:/downloads \
  -v $(pwd)/items:/items \
  grab-ia:latest \
  start --items /items/items.txt --output /downloads \
  --extensions mp3,flac --workers 16 --speed-limit 10
```

### 4. Metadata only
```bash
docker run -it --rm \
  -v $(pwd)/downloads:/downloads \
  -v $(pwd)/items:/items \
  grab-ia:latest \
  start --items /items/items.txt --output /downloads \
  --metadata-only --workers 4
```

### 5. Interactive shell (debugging)
```bash
docker run -it --rm \
  -v $(pwd)/downloads:/downloads \
  -v $(pwd)/items:/items \
  --entrypoint /bin/bash \
  grab-ia:latest
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OUTPUT_DIR` | Default output directory | `/downloads` |
| `DISPLAY` | X11 display for GUI mode | `:0` |

## Volume Mounts

| Container Path | Purpose | Required |
|----------------|---------|----------|
| `/downloads` | Downloaded files and state database | Yes |
| `/items` | Item list files (TXT/CSV) | Yes (for start) |

## Networking

### Headless mode
- Uses bridge network by default
- No special configuration needed
- Outbound connections only

### GUI mode
- Requires `network_mode: host` for X11
- Requires X11 socket mount
- May need `xhost` configuration

## Performance Optimization

### CPU/Memory limits
```bash
docker run -it --rm \
  --cpus="4.0" \
  --memory="2g" \
  -v $(pwd)/downloads:/downloads \
  -v $(pwd)/items:/items \
  grab-ia:latest \
  start --items /items/items.txt --output /downloads
```

### Bandwidth limiting
```bash
docker run -it --rm \
  -v $(pwd)/downloads:/downloads \
  -v $(pwd)/items:/items \
  grab-ia:latest \
  start --items /items/items.txt --output /downloads \
  --speed-limit 50  # 50 MB/s
```

## Running as a Service (systemd)

Create `/etc/systemd/system/grab-ia.service`:

```ini
[Unit]
Description=grab-IA Downloader
After=docker.service
Requires=docker.service

[Service]
Type=simple
Restart=always
RestartSec=10
ExecStartPre=-/usr/bin/docker stop grab-ia-service
ExecStartPre=-/usr/bin/docker rm grab-ia-service
ExecStart=/usr/bin/docker run --name grab-ia-service \
  -v /data/grab-ia/downloads:/downloads \
  -v /data/grab-ia/items:/items \
  grab-ia:latest \
  start --items /items/items.txt --output /downloads --workers 8
ExecStop=/usr/bin/docker stop grab-ia-service

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable grab-ia.service
sudo systemctl start grab-ia.service
sudo systemctl status grab-ia.service
```

## Kubernetes Deployment

### Job (one-time download)
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: grab-ia-job
spec:
  template:
    spec:
      containers:
      - name: grab-ia
        image: grab-ia:latest
        args: ["start", "--items", "/items/items.txt", "--output", "/downloads", "--workers", "8"]
        volumeMounts:
        - name: downloads
          mountPath: /downloads
        - name: items
          mountPath: /items
      restartPolicy: OnFailure
      volumes:
      - name: downloads
        persistentVolumeClaim:
          claimName: grab-ia-downloads-pvc
      - name: items
        configMap:
          name: grab-ia-items
```

### CronJob (scheduled downloads)
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: grab-ia-daily
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: grab-ia
            image: grab-ia:latest
            args: ["resume", "--output", "/downloads", "--workers", "8"]
            volumeMounts:
            - name: downloads
              mountPath: /downloads
          restartPolicy: OnFailure
          volumes:
          - name: downloads
            persistentVolumeClaim:
              claimName: grab-ia-downloads-pvc
```

## Troubleshooting

### Permission issues
```bash
# Run with specific user ID
docker run -it --rm \
  --user $(id -u):$(id -g) \
  -v $(pwd)/downloads:/downloads \
  -v $(pwd)/items:/items \
  grab-ia:latest \
  start --items /items/items.txt --output /downloads
```

### GUI not working
```bash
# Check X11 authentication
xhost +local:docker

# Verify DISPLAY variable
echo $DISPLAY

# Test with simple X11 app
docker run --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix xeyes
```

### Container exits immediately
```bash
# Check logs
docker logs <container_id>

# Run interactively
docker run -it grab-ia:latest /bin/bash
```

### Network issues
```bash
# Test connectivity from container
docker run --rm grab-ia:latest python -c "import requests; print(requests.get('https://archive.org').status_code)"
```

## Security Best Practices

1. **Don't run as root**
   ```bash
   docker run --user 1000:1000 ...
   ```

2. **Use read-only root filesystem**
   ```bash
   docker run --read-only -v /downloads:/downloads ...
   ```

3. **Limit capabilities**
   ```bash
   docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE ...
   ```

4. **Use secrets for credentials**
   ```bash
   docker run --secret ia_credentials ...
   ```

## Multi-Architecture Support

Build for multiple architectures:
```bash
docker buildx create --name multiarch --use
docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 -t grab-ia:latest --push .
```

## Cleanup

### Remove stopped containers
```bash
docker container prune
```

### Remove unused images
```bash
docker image prune -a
```

### Remove all grab-ia data
```bash
docker-compose down -v
rm -rf downloads items
```
