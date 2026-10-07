# 智能科研助理 - RAG 后端（模块一 + 模块二）

基于 **RAG + Agent** 的论文知识库问答系统后端实现，负责：
- 模块一：文档处理与检索层（PDF 加载、3 种分块策略、向量检索、BM25、RRF 融合、重排序）
- 模块二：RAG 生成层（Prompt 模板、引用溯源、端到端问答）

## 环境要求
- Python 3.10
- CUDA 12.0+（可选，CPU 也能跑）
- Ollama（用于 LLM 推理）

## 快速开始

### 1. 创建环境
conda create -n rag_env python=3.10 -y
conda activate rag_env
pip install -r requirements.txt

### 2. 下载模型（用 ModelScope）
mkdir -p /root/autodl-tmp/models/bge-large-zh
modelscope download --model AI-ModelScope/bge-large-zh-v1.5 --local_dir /root/autodl-tmp/models/bge-large-zh

mkdir -p /root/autodl-tmp/models/bge-reranker-base
modelscope download --model BAAI/bge-reranker-base --local_dir /root/autodl-tmp/models/bge-reranker-base

### 3. 启动 Ollama 并导入 Qwen2.5
curl -fsSL https://ollama.com/install.sh | sh
export OLLAMA_MODELS=/root/autodl-tmp/models
nohup ollama serve > /root/autodl-tmp/ollama.log 2>&1 &

cd /root/autodl-tmp/models/qwen2.5
cat > Modelfile << 'MODELEOF'
FROM ./qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf
MODELEOF
ollama create qwen2.5:7b -f Modelfile

### 4. 使用 RAG
python
>>> from src.generation import build_index, retrieve, rag_answer
>>> build_index()
>>> docs = retrieve("What is multi-head attention?", top_k=3)
>>> result = rag_answer("What dataset was used for training?")
>>> print(result["answer"])

## 目录结构
src/data_loader/    - PDF/Word/TXT 文档加载
src/chunking/       - 3 种分块策略 + 对比实验
src/retrieval/      - 向量检索 + BM25 + RRF + Reranker
src/generation/     - RAG 生成层（对外接口）
data/               - 上传的 PDF 论文
vector_store/       - Chroma 持久化目录
logs/               - 实验数据

## 对外接口
- build_index(files=None, chunk_size=512, overlap=50) -> int
- retrieve(query, top_k=5) -> List[Dict]
- rag_answer(query, top_k=5, temperature=0.1) -> Dict

详见 docs/rag_interface.md

## 作者
南京农业大学 智慧农业学院
生产实习课程项目 - 成员 C（RAG 后端开发）
