# Building the ACE Controller Container for the Multilingual App

Follow these steps to build and push the `ace-controller` container for the multilingual app.

---

### 🚀 Step 1: Clone the Repository

```bash
git clone https://github.com/bhsanjan/tokkio-5.0.0-beta-hackathon.git
```

### 📂 Step 2: Navigate to the Project Directory
```bash
cd tokkio-5.0.0-beta-hackathon/multi-lingual-app-source/llm-rag
```

### 🛠️ Step 3: Build the Docker Image
```bash
docker build -t nvcr.io/<MY_ORG>/<MY_TEAM>/ace-controller:<MY_VERSION> .
```

### 📤 Step 4: Push the Docker Image
```bash
docker push nvcr.io/<MY_ORG>/<MY_TEAM>/ace-controller:<MY_VERSION>
```