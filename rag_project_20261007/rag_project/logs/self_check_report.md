# 模块 C 交付自检报告
生成时间: 2026-10-07 15:07:37

## 1. 项目结构
./README.md
./data/attention_is_all_you_need.pdf
./logs/chunk_experiment.csv
./logs/self_check_report.md
./requirements.txt
./src/__init__.py
./src/chunking/__init__.py
./src/chunking/chunker.py
./src/chunking/experiment.py
./src/data_loader/__init__.py
./src/data_loader/pdf_loader.py
./src/generation/__init__.py
./src/generation/rag_pipeline.py
./src/retrieval/__init__.py
./src/retrieval/bm25_retriever.py
./src/retrieval/hybrid_retriever.py
./src/retrieval/reranker.py
./src/retrieval/vector_store.py

## 2. 关键文件
  ✅ README.md
  ✅ requirements.txt
  ❌ docs/rag_interface.md 缺失
  ✅ src/data_loader/pdf_loader.py
  ✅ src/chunking/chunker.py
  ✅ src/chunking/experiment.py
  ✅ src/retrieval/vector_store.py
  ✅ src/retrieval/bm25_retriever.py
  ✅ src/retrieval/reranker.py
  ✅ src/retrieval/hybrid_retriever.py
  ✅ src/generation/__init__.py
  ✅ src/generation/rag_pipeline.py

## 3. Ollama 模型
NAME          ID              SIZE      MODIFIED          
qwen2.5:7b    2cf59abf1e1b    4.7 GB    About an hour ago    

## 4. 分块实验数据
method,chunk_size,num_chunks,avg_len,min_len,max_len
fixed,256,161,243.2,31,256
fixed,512,83,469.5,77,512
fixed,1024,43,892.3,155,1024
recursive,256,170,208.0,54,256
recursive,512,82,432.2,70,512
recursive,1024,40,887.1,89,1021
semantic,256,167,211.7,1,792
semantic,512,86,412.1,48,792
semantic,1024,42,844.9,221,1023
