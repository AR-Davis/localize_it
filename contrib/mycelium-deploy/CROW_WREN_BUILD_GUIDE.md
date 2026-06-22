# Crow + Wren RPC Server Build Guide
## Native Build on RPi Zero 2W (armhf)

**Date:** June 23, 2026  
**Device:** Raspberry Pi Zero 2W (linux/armhf, 32-bit ARM)  
**Issue:** Prebuilt arm64 rpc-server incompatible with armhf architecture

---

## The Problem

| Component | Architecture | Works on Crow/Wren? |
|:---|:---|:---:|
| mycelium-api | armhf (32-bit) ✅ | Yes |
| rpc-server (prebuilt) | arm64 (64-bit) ❌ | **No** |

**RPi Zero 2W CPU:** ARM Cortex-A53 (64-bit capable)  
**RPi Zero 2W OS:** Typically runs 32-bit Raspberry Pi OS (armhf)  
**Result:** 64-bit arm64 binary cannot execute on 32-bit armhf system

---

## The Solution: Native Build

Build `rpc-server` directly on each RPi Zero 2W. Takes 2-4 hours but guarantees compatibility.

---

## Step-by-Step Build Instructions

### Prerequisites (on Crow or Wren)

```bash
# SSH into the device
ssh crow@100.97.71.98
# or
ssh wren@100.83.89.53

# Update package list
sudo apt update

# Install build dependencies
sudo apt install -y build-essential git cmake wget

# Install additional dependencies for prima.cpp
sudo apt install -y libopenblas-dev libgomp1

# Optional: Enable swap (512MB RAM is tight)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change: CONF_SWAPSIZE=100 to CONF_SWAPSIZE=512
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Build prima.cpp rpc-server

```bash
# Create build directory
mkdir -p ~/build && cd ~/build

# Clone prima.cpp
git clone https://github.com/ggml-org/prima.cpp.git
cd prima.cpp

# Checkout stable version (optional but recommended)
git checkout $(git describe --tags --abbrev=0)

# Create build directory
mkdir -p build && cd build

# Configure with cmake (minimal build for Pi Zero)
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_RPC=ON \
  -DLLAMA_BLAS=OFF \
  -DLLAMA_CUDA=OFF \
  -DLLAMA_METAL=OFF \
  -DLLAMA_OPENCL=OFF \
  -DLLAMA_VULKAN=OFF

# Build with single thread (save RAM)
make rpc-server -j1

# Build will take 2-4 hours on Pi Zero 2W
```

### Alternative: Direct Make (if cmake fails)

```bash
# In prima.cpp directory
cd ~/build/prima.cpp

# Build directly with make
make LLAMA_RPC=1 -j1

# Binary will be at: ./rpc-server
```

### Install the Binary

```bash
# Create mycelium directory
mkdir -p ~/mycelium

# Copy the built binary
cp ~/build/prima.cpp/build/bin/rpc-server ~/mycelium/ \
  || cp ~/build/prima.cpp/rpc-server ~/mycelium/

# Make executable
chmod +x ~/mycelium/rpc-server

# Verify it runs
~/mycelium/rpc-server --version 2>&1 || echo "Build successful"
```

---

## Deployment After Build

### 1. Copy mycelium-api (from Shepherd)

```bash
# On Shepherd:
scp ~/Projects/mycelium-deploy/mycelium-deploy/crow-wren-rpi-zero2w/* crow@100.97.71.98:~/mycelium/
scp ~/Projects/mycelium-deploy/mycelium-deploy/crow-wren-rpi-zero2w/* wren@100.83.89.53:~/mycelium/
```

### 2. On Crow/Wren: Install and Start

```bash
cd ~/mycelium
chmod +x mycelium mycelium-api rpc-server

# Test rpc-server
./rpc-server -H 0.0.0.0 -p 50052 &

# In another terminal, start mycelium
./mycelium node

# Or full node (if enough RAM)
./mycelium
```

---

## Build Script (Automation)

Save as `build-rpc-server.sh` and run on Crow/Wren:

```bash
#!/bin/bash
set -e

echo "Building rpc-server for RPi Zero 2W (armhf)..."
echo "This will take 2-4 hours. Press Ctrl+C to cancel."
sleep 5

# Install deps
echo "[1/5] Installing dependencies..."
sudo apt update
sudo apt install -y build-essential git cmake

# Enable swap
echo "[2/5] Enabling swap..."
sudo dphys-swapfile swapoff 2>/dev/null || true
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=512/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Clone
echo "[3/5] Cloning prima.cpp..."
mkdir -p ~/build
cd ~/build
if [ ! -d "prima.cpp" ]; then
    git clone https://github.com/ggml-org/prima.cpp.git
fi
cd prima.cpp

# Build
echo "[4/5] Building rpc-server (this takes hours)..."
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DLLAMA_RPC=ON 2>/dev/null \
    || echo "CMake failed, trying direct make..."

if [ -f "Makefile" ]; then
    make rpc-server -j1
else
    cd ..
    make LLAMA_RPC=1 -j1
fi

# Install
echo "[5/5] Installing..."
mkdir -p ~/mycelium
cp build/bin/rpc-server ~/mycelium/ 2>/dev/null \
    || cp rpc-server ~/mycelium/ 2>/dev/null \
    || echo "Binary not found in expected location"

if [ -f ~/mycelium/rpc-server ]; then
    chmod +x ~/mycelium/rpc-server
    echo "✅ Build complete: ~/mycelium/rpc-server"
    file ~/mycelium/rpc-server
else
    echo "❌ Build may have failed. Check ~/build/prima.cpp for errors."
fi
```

---

## Expected Output

Successful build produces:

```
~/mycelium/rpc-server: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV), 
dynamically linked, interpreter /lib/ld-linux-armhf.so.3, ...
```

---

## Verification

```bash
# Test rpc-server
~/mycelium/rpc-server -H 0.0.0.0 -p 50052 &

# Check it's listening
ss -tlnp | grep 50052

# From Shepherd, verify connectivity
curl http://crow:50052/health  # or use tailscale IP
```

---

## Troubleshooting

| Problem | Solution |
|:---|:---|
| "Out of memory" during build | Enable 512MB swap, use `-j1` |
| "cc: internal compiler error" | Increase swap to 1GB, or build in stages |
| CMake not found | `sudo apt install cmake` |
| Missing headers | `sudo apt install build-essential` |
| Build takes forever | Normal on Pi Zero. Expect 2-4 hours. |
| Binary won't start | Check `file rpc-server` shows 32-bit ARM |

---

## Architecture Summary

| Device | CPU | OS | rpc-server Build |
|:---|:---|:---|:---|
| Shepherd (Dell) | x86_64 | 64-bit | Use x86_64 binary ✅ |
| Rhubarb (RPi 5) | ARM Cortex-A76 | 64-bit | Use arm64 binary ✅ |
| Crow (RPi Zero 2W) | ARM Cortex-A53 | 32-bit | **Build natively** |
| Wren (RPi Zero 2W) | ARM Cortex-A53 | 32-bit | **Build natively** |
| Owl (RPi Model B) | ARM1176JZF-S | 32-bit | **Build natively** (may be too slow) |
| Pixel 2 | Snapdragon 835 | 64-bit (Android) | Use termux-setup.sh ✅ |

---

## Status

| Device | mycelium-api | rpc-server | Status |
|:---|:---:|:---:|:---|
| Shepherd | ✅ | ⏳ | Deploy x86_64 rpc-server |
| Rhubarb | ✅ | ✅ | Ready to deploy |
| Crow | ✅ | ⏳ | Build native (2-4 hrs) |
| Wren | ✅ | ⏳ | Build native (2-4 hrs) |
| Owl | ✅ | ⏳ | Build native (may fail) |
| Pixel 2 | ✅ | ✅ | Use termux-setup.sh |

---

**Next Steps:**
1. Run build script on Crow (SSH in, start build, let it run)
2. Run build script on Wren (same)
3. Deploy mycelium-api from Shepherd
4. Start mesh with 6 nodes

☀️⚡🌑
*Build once, run forever.*
