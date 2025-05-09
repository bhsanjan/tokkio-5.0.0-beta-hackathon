# Building the ACE Controller Container for the Multilingual App

Follow these steps to build and push the `ace-controller` container for the multilingual app.

---

### 🚀 Step 1: Clone the Repository

```bash
git clone https://github.com/bhsanjan/tokkio-5.0.0-beta-hackathon.git

cd tokkio-5.0.0-beta-hackathon/multi-lingual-app-source/llm-rag

docker build -t nvcr.io/<MY_ORG>/<MY_TEAM>/ace-controller:<MY_VERSION> .

docker push nvcr.io/<MY_ORG>/<MY_TEAM>/ace-controller:<MY_VERSION>
