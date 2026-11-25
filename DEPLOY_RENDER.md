# 🚀 Deploy CampusCopilot on Render.com — Step by Step

> **Time needed:** ~15 minutes  
> **Cost:** Free (Render free tier with 1 GB persistent disk)  
> **Result:** A public HTTPS URL like `https://campuscopilot-xxxx.onrender.com`

---

## Prerequisites

Before starting, make sure you have:

1. ✅ A **GitHub account** — [github.com](https://github.com)
2. ✅ A **Render account** — [render.com](https://render.com) (sign up free with GitHub)
3. ✅ An **Anthropic API key** — [console.anthropic.com](https://console.anthropic.com)

---

## Step 1: Push Your Code to GitHub

### 1a. Create a new GitHub repository

1. Go to [github.com/new](https://github.com/new)
2. Repository name: **`campuscopilot`**
3. Set it to **Private** (recommended)
4. Do **NOT** check "Add README" (you already have one)
5. Click **Create repository**

### 1b. Push your local code

Open a terminal in your project folder and run:

```bash
git init
git add .
git commit -m "CampusCopilot - production ready"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/campuscopilot.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

> **Important:** The `.gitignore` already excludes `.env`, `secrets.toml`, database files, and uploads. No secrets will be pushed.

---

## Step 2: Create a Web Service on Render

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Click **"Build and deploy from a Git repository"** → Next
4. Connect your GitHub account and select your **`campuscopilot`** repository
5. Configure:

| Setting | Value |
|---|---|
| **Name** | `campuscopilot` |
| **Region** | Closest to you (e.g. `Singapore` for India) |
| **Branch** | `main` |
| **Runtime** | **Docker** ⚠️ (not Python!) |
| **Instance Type** | **Free** |

6. Click **"Create Web Service"**

---

## Step 3: Add a Persistent Disk

1. In your service dashboard → **"Disks"** tab
2. Click **"Add Disk"**:

| Setting | Value |
|---|---|
| **Name** | `campuscopilot-data` |
| **Mount Path** | `/data` |
| **Size** | `1` GB |

3. Click **"Save"**

---

## Step 4: Set Environment Variables

Go to **"Environment"** tab → add each variable:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-your-real-key` |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` |
| `DATABASE_PATH` | `/data/campus.db` |
| `CHROMA_PERSIST_DIRECTORY` | `/data/chroma` |
| `DOCUMENT_STORAGE_PATH` | `/data/uploads` |
| `ADMIN_PASSWORD` | `YourStrongPassword123` |
| `OFFICER_PASSWORD` | `YourStrongPassword456` |

Click **"Save Changes"** → Render will redeploy automatically.

---

## Step 5: Wait & Access

1. Watch **"Events"** tab for build progress (~3-5 min)
2. When you see **"Your service is live 🎉"**, click the URL at the top:
   ```
   https://campuscopilot-xxxx.onrender.com
   ```
3. Login as `admin` / your ADMIN_PASSWORD
4. Upload college PDFs → Upload & Index tab
5. Create a student account → test AI Chat

---

## Updating Your App

```bash
git add .
git commit -m "update description"
git push origin main
```

Render auto-deploys on push. Data on persistent disk is preserved.

---

## Notes

- Free tier sleeps after 15 min of inactivity (30-60s wakeup on first request)
- Paid tier ($7/month) keeps app always-on
- Persistent disk survives restarts and redeploys
