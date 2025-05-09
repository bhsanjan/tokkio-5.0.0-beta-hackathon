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

# Using the existing helm chart for deployment with updated container

### 🚀 Step 1: Clone the Repository
```bash
git clone https://github.com/bhsanjan/tokkio-5.0.0-beta-hackathon.git
```

### 📂 Step 2: Navigate to the Project Directory
```bash
cd tokkio-5.0.0-beta-hackathon/multi-lingual-app-source/reference-helm-chart
```

### 📂 Step 3: untar the helm chart
```bash
tar -xzvf tokkio-5.0.0-beta.tgz
```

### 🛠️ Step 4: Navigate to the file and update the container you created in the previous
```bash
cd tokkio/charts/tokkio-app/
vi values.yaml

Update the value and tag accordingly for these fields for the ace-controller spec

          - name: IMAGE_NAME
            value: nvcr.io/0690032576501076/prod-test/ace-controller
          - name: IMAGE_TAG
            value: 5.0.5-beta
          image:
            repository: nvcr.io/0690032576501076/prod-test/ace-controller
            tag: 5.0.5-beta
  image: nvcr.io/0690032576501076/prod-test/ace-controller
  imagePullSecrets:
  - name: ngc-docker-reg-secret
  tag: 5.0.5-beta
```

### 📤 Step 5: Use the chart for deployment either locally or using scripts
```bash
tar -czvf tokkio-5.0.0-new-app.tgz tokkio
```