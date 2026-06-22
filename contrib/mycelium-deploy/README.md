# Mycelium Deploy — Complete Package

Two pieces per device:
1. **mycelium-api** — the gateway/router (Go binary, cross-compiled, ready to run)
2. **rpc-server** — the compute engine (prima.cpp binary, may need native build)

---

## What's In This Folder

```
mycelium-deploy/
├── README.md              ← you are here
├── shepherd-dell-latitude/  ← mycelium-api for Shepherd (linux/amd64)
├── rhubarb-rpi5/            ← mycelium-api for Rhubarb (linux/arm64)
├── crow-wren-rpi-zero2w/    ← mycelium-api for Crow/Wren (linux/armhf)
├── owl-rpi-model-b/         ← mycelium-api for Owl (linux/armhf)
└── rpc-servers/
    ├── arm64/rpc-server      ← static ARM64 binary (for Pi 5, Pi Zero 2W)
    ├── x86_64/rpc-server     ← x86-64 binary (for Shepherd, Ember)
    └── termux-setup.sh       ← Android/Pixel 2 setup (builds natively in Termux)
```

---

## DEPLOYING A DEVICE

### Step 1: Install mycelium-api (the gateway)

```bash
# Copy the right package to the device
scp -r shepherd-dell-latitude/ user@device:~/mycelium/

# On the device:
cd ~/mycelium
chmod +x mycelium mycelium-api install.sh
./install.sh
```

### Step 2: Install rpc-server (the compute engine)

This is the prima.cpp binary that actually does the tensor math. Each device needs one.

#### Option A: Use the prebuilt binary (try this first)

```bash
# For ARM64 devices (Pi 5, Pi Zero 2W):
scp rpc-servers/arm64/rpc-server user@device:~/mycelium/

# For x86_64 devices (Shepherd, Ember, other PCs):
scp rpc-servers/x86_64/rpc-server user@device:~/mycelium/

# On the device:
cd ~/mycelium
chmod +x rpc-server
./rpc-server -H 0.0.0.0 -p 50052
```

If you get "Bad system call" or "cannot execute binary file", the prebuilt
binary doesn't match the device's libc. Use Option B.

#### Option B: Build natively on the device (guaranteed to work)

```bash
# On the device:
sudo apt install build-essential git
git clone https://github.com/ggml-org/prima.cpp.git
cd prima.cpp
make USE_HIGHS=1 LLAMA_RPC=1 -j$(nproc)
# Binary will be at: ./build/bin/rpc-server

# Copy it next to mycelium-api:
cp build/bin/rpc-server ~/mycelium/

# Start it:
cd ~/mycelium
./rpc-server -H 0.0.0.0 -p 50052
```

#### Option C: Termux/Android (Pixel 2)

```bash
# From TheTower:
adb push rpc-servers/termux-setup.sh /sdcard/

# In Termux on the phone:
bash /sdcard/termux-setup.sh
rpc-server -H 0.0.0.0 -p 50052
```

### Step 3: Start the mesh

```bash
# Start compute node (rpc-server) in one terminal:
./rpc-server -H 0.0.0.0 -p 50052

# Start the gateway (mycelium-api) in another:
mycelium          # full node (API + compute)
mycelium api      # API gateway only
mycelium node     # just the rpc-server (wrapper)
mycelium status   # check all nodes
```

### Step 4: Edit the config

```bash
nano ~/.mycelium/mycelium.yaml
```

Set the real Tailscale IPs for each node:
```yaml
nodes:
  - name: hearth
    host: 100.64.0.1      # real Tailscale IP
    port: 11434
    protocol: ollama
    weight: 100
  - name: ember
    host: 100.90.116.1
    port: 50052
    protocol: rpc
    weight: 10
  - name: pixel2
    host: 100.77.170.98
    port: 50052
    protocol: rpc
    weight: 30
```

---

## DEVICE-SPECIFIC NOTES

### Shepherd (Dell Latitude) — linux/amd64
- Prebuilt x86_64 rpc-server may work (dynamically linked, needs libzmq, libhighs)
- If it fails, build natively: `make USE_HIGHS=1 LLAMA_RPC=1`
- Full node: runs both API gateway and compute

### Rhubarb (RPi 5) — linux/arm64
- ARM64 static binary should work (statically linked, no deps)
- Full node: runs both API gateway and compute
- RPi 5 has 4-8GB RAM, should handle small models

### Crow/Wren (RPi Zero 2W) — linux/armhf (32-bit)
- The ARM64 binary will NOT work (needs 64-bit)
- Must build natively: `make USE_HIGHS=1 LLAMA_RPC=1` on the Pi Zero
- Compute only: 512MB RAM is tight, use smallest models only

### Owl (RPi Model B) — linux/armhf (32-bit)
- Same as Crow/Wren — build natively
- Compute only: very limited (256-512MB RAM)
- May not be viable for inference, could be a relay only

### Pixel 2 (Android/Termux)
- Must build natively in Termux (cross-compiled binaries fail on Bionic libc)
- Use the termux-setup.sh script
- Compute only: works on port 50052, Android doesn't block it

---

## TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| "Bad system call" | Binary doesn't match libc. Build natively. |
| "cannot execute binary file" | Wrong architecture. Check with `file rpc-server`. |
| Connection refused on 50052 | rpc-server not running, or firewall blocking. Start with `-H 0.0.0.0`. |
| Tailscale IP unreachable | Device not on Tailscale, or Tailscale not running. `tailscale status` on both ends. |
| mycelium command not found | Run `./install.sh` again, or check `~/.local/bin` is in PATH. |
