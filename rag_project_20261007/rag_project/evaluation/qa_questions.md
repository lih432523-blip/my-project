# 55 题评测问题与参考答案

分类为事实20、对比15、归纳10、推理10。每题参考答案依据本地原始PDF核对，页码为从1开始的PDF物理页码。实际机器回答需另行运行并评分。

## 事实题

### F01 《An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale》如何把图像转换为 Transformer 的输入？训练任务是什么？

参考答案：先将图像分成 patch，对每个 patch 作线性嵌入，将这些嵌入组成序列输入 Transformer；图像 patch 被当作 NLP 中的 token 处理。模型以监督方式训练执行图像分类。

原文依据：

- `An_Image_is_Worth_16x16_Words.pdf`，PDF第1页。

> To do so, we split an image into patches and provide the sequence of linear embeddings of these patches as an input to a Trans- former. Image patches are treated the same way as tokens (words) in an NLP application. We train the model on image classification in supervised fashion.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F02 《Deep Residual Learning for Image Recognition》在 ImageNet 上评估的残差网络最深是多少层？残差网络集成在 ImageNet 测试集上的错误率是多少？

参考答案：最大深度为152层；残差网络集成在ImageNet测试集上的错误率为3.57%。

原文依据：

- `Deep_Residual_Learning_for_Image_Recognition.pdf`，PDF第1页。

> On the ImageNet dataset we evaluate residual nets with a depth of up to 152 layers—8 × deeper than VGG nets [40] but still having lower complex- ity. An ensemble of these residual nets achieves 3.57% error on the ImageNet test set.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F03 《Attention Is All You Need》在 WMT 2014 英德、英法翻译任务上分别报告多少 BLEU？摘要给出的英法模型训练时长和 GPU 数量是多少？

参考答案：英德任务为28.4 BLEU；英法任务为41.8 BLEU。摘要报告英法模型在8块GPU上训练3.5天。

原文依据：

- `attention_is_all_you_need.pdf`，PDF第1页。

> Our model achieves 28.4 BLEU on the WMT 2014 English- to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs,

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F04 《Video-LLaVA: Learning United Visual Representation by Alignment Before Projection》摘要列出的四个视频基准是什么？相对 Video-ChatGPT 各自报告了多少提升？

参考答案：按摘要顺序，MSRVTT、MSVD、TGIF、ActivityNet的提升分别是5.8%、9.9%、18.6%、10.1%；这些数字对应论文摘要报告的提升，不是模型的绝对得分。

原文依据：

- `2311.10122v3.pdf`，PDF第1页。

> Video-LLaV A outperforms Video-ChatGPT by 5.8%, 9.9%, 18.6%, and 10.1% on MSRVTT, MSVD, TGIF, and ActivityNet, respectively.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F05 《Vision Mamba: Efficient Visual Representation Learning with Bidirectional State Space Model》在 1248×1248 图像的批量特征提取实验中，相对 DeiT 的速度和 GPU 显存结果是什么？

参考答案：Vim的速度为DeiT的2.8倍，并节省86.8% GPU显存；该结果限定为1248×1248图像的批量推理特征提取场景。

原文依据：

- `2401.09417v3.pdf`，PDF第2页。

> Specifically, Vim is 2.8× faster than DeiT and saves 86.8% GPU memory when performing batch inference to extract features on images at the resolution of 1248×1248.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F06 《How to Choose a Suitable Method in Image Semantic Segmentation—An Experimental Study》实验具体评估了哪六个网络版本？

参考答案：六个版本为DenseNet201、EfficientNetB7、InceptionResNetV2、InceptionV3、ResNet152V2和VGG16。

原文依据：

- `How_to_Choose_a_Suitable_Method_in_Image_Semantic_Segmentation-An_Experimental_Study.pdf`，PDF第1页。

> specifically six methods including DenseNet201, EfficientNetB7, InceptionResNetV2, InceptionV3, ResNet152V2 and VGG16.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F07 《How to Benchmark Vision Foundation Models for Semantic Segmentation?》推荐用哪种模型规模、patch 大小和解码器进行基准测试？摘要报告训练时间减少多少倍？

参考答案：推荐对VFM的ViT-B版本进行微调，采用16×16 patch和线性解码器。摘要称该设置能代表更大模型、更复杂解码器和更小patch的排序，同时将训练时间减少超过13倍。

原文依据：

- `Kerssies_How_to_Benchmark_Vision_Foundation_Models_for_Semantic_Segmentation_CVPRW_2024_paper.pdf`，PDF第1页。

> the recommendation is to fine- tune the ViT-B variants of VFMs with a 16 × 16 patch size and a linear decoder, as these settings are representative of using a larger model, more advanced decoder and smaller patch size, while reducing training time by more than 13 times.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F08 《Multi-View Semantic–Geometric Perception for Post-Disaster Flexible Suction with Metric 3D Scene Reconstruction》摘要中 YOLO-LiteSeg 的参数量和 GFLOPs 分别由多少降到多少？推理时间是多少？

参考答案：参数量从27.24 M降至2.61 M；GFLOPs从52.37降至5.47；推理时间为4.56 ms。这些结果来自九种模拟条件。

原文依据：

- `applsci-16-10003.pdf`，PDF第1页。

> Across nine simulated conditions, YOLO-LiteSeg reduced parameters from 27.24 M to 2.61 M and giga floating-point operations from 52.37 to 5.47, while achieving 99.02% mean average precision at 0.50 intersection over union and 84.36% across thresholds from 0.50 to 0.95, with 4.56 ms inference.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F09 《SBRF-Det: Scale-Boundary Representative Fusion for Multi-Finding Detection in Panoramic Dental Radiographs》使用的 OralXrays-9 有多少张影像、多少个保留标注和多少类？固定留出队列是多少张？

参考答案：OralXrays-9包含12,688张全景牙科影像、84,099个保留标注，分为9类；固定留出队列含2,688张影像。

原文依据：

- `diagnostics-16-03259.pdf`，PDF第1页。

> The method was evaluated on OralXrays-9, comprising 12,688 panoramic radiographs and 84,099 retained annotations across nine categories, using a fixed 2688-image hold-out cohort.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F10 《A Thermal-Aware Infrared–Visible Image Fusion Method for Defect Detection in Power Transmission Equipment》融合图像通过统一 YOLO 检测器评估时，precision、recall 和 IoU=0.5 的 mAP 各是多少？

参考答案：precision为0.936，recall为0.921，IoU=0.5的mAP为0.943；顺序不能颠倒。

原文依据：

- `energies-19-04788.pdf`，PDF第1页。

> When the fused images are evaluated using a unified YOLO-based detector, the proposed thermal- aware fusion framework achieves precision, recall, and mAP at IoU = 0.5 values of 0.936, 0.921, and 0.943, respectively.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F11 《Vision-Guided Cone Manipulation with Collaborative Robotic Arm》如何用重量验证抓取成功？抓取失败最多会自动重试几次？

参考答案：利用协作机械臂内置力传感能力，比较抓取前后测得的负载进行重量验证；失败抓取最多自动触发三次重试。

原文依据：

- `engproc-157-00021.pdf`，PDF第1页。

> Grasp reliability is enhanced through a weight-based validation method utilizing the collaborative robot’s built-in force sensing capability. The measured load before and after grasping is compared, and unsuc- cessful grasps automatically trigger up to three retry attempts.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F12 《Occlusion-Aware Watermelon Size Estimation Using YOLO11-OBB and Amodal GAN》摘要报告的分割 IoU、Dice 和 boundary F1-score 分别是多少？

参考答案：IoU为0.846，Dice为0.915，boundary F1-score为0.959。

原文依据：

- `engproc-159-00004.pdf`，PDF第1页。

> The effectiveness of the framework was proven since it showed segmentation performance with an intersection over union of 0.846, a dice of 0.915, and a boundary F1-score of 0.959.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F13 《An Intelligent Framework for Tooth Segmentation and Classification Through Fusion of Transfer Learning with Advanced Optimization Algorithms Using Biomedical Images》的基准牙科 X 光数据集包含多少图像和多少牙齿类别？

参考答案：该基准牙科X光数据集包含598张图像和32个牙齿类别。

原文依据：

- `oral-06-00131.pdf`，PDF第1页。

> The proposed framework is evaluated on a benchmark dental X-ray image dataset containing 598 images and 32 tooth classes.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F14 《Zero-Shot Water Monitoring from Fixed Drainage Surveillance Imagery Across Day/Night and Rain/No-Rain Conditions: A SAM 3 Benchmark at 25 Urban Sites》的基准包含多少帧、来自多少台固定摄像机？调用 SAM 3 的文本提示词是什么？

参考答案：基准含3651帧，来自镇江城市排水监测网络的25台固定摄像机；SAM 3使用文本提示词“water”。

原文依据：

- `sensors-26-06403.pdf`，PDF第1页。

> We construct a benchmark of 3651 frames from 25 fixed cameras of an urban drainage monitoring network in Zhenjiang, China,

- `sensors-26-06403.pdf`，PDF第1页。

> Using SAM 3 with the text prompt “water”, we extract per‐frame water‐area ratio and normalized waterline level,

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F15 《Constructing a Xiangyunsha Defect Dataset and a Lightweight Detection Model for Sustainability》数据集共有多少张标注图像？训练、验证和留出测试各有多少张？

参考答案：共1831张标注图像；训练集1400张、验证集331张、留出测试集100张；模型开发仅使用训练和验证子集。

原文依据：

- `sustainability-18-10291.pdf`，PDF第1页。

> dataset comprising 1831 annotated images. In the revised experimental protocol, the dataset was divided into 1400 training, 331 validation, and 100 held‐out test images, with all model development experiments conducted using only the training and validation sub‐ sets.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F16 《An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale》4.1 节中用于探索可扩展性的三个预训练数据集分别有多少类和多少图像？

参考答案：ILSVRC-2012 ImageNet为1k类、1.3M图像；ImageNet-21k为21k类、14M图像；JFT为18k类、303M高分辨率图像。

原文依据：

- `An_Image_is_Worth_16x16_Words.pdf`，PDF第4页。

> Datasets. To explore model scalability, we use the ILSVRC-2012 ImageNet dataset with 1k classes and 1.3M images (we refer to it as ImageNet in what follows), its superset ImageNet-21k with 21k classes and 14M images (Deng et al., 2009), and JFT (Sun et al., 2017) with 18k classes and 303M high-resolution images.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F17 《Deep Residual Learning for Image Recognition》ImageNet 训练使用什么优化器、mini-batch、初始学习率、weight decay 和 momentum？是否使用 dropout？

参考答案：使用SGD，mini-batch=256；初始学习率0.1，误差进入平台期时除以10；weight decay=0.0001，momentum=0.9；不使用dropout。

原文依据：

- `Deep_Residual_Learning_for_Image_Recognition.pdf`，PDF第4页。

> We use SGD with a mini-batch size of 256. The learning rate starts from 0.1 and is divided by 10 when the error plateaus, and the models are trained for up to 60 × 104 iterations. We use a weight decay of 0.0001 and a momentum of 0.9. We do not use dropout [13],

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F18 《Attention Is All You Need》3.1 节描述的编码器、解码器分别堆叠几层？各子层及嵌入层输出维度是多少？

参考答案：编码器和解码器均为N=6层；各子层和嵌入层的输出维度d_model=512。

原文依据：

- `attention_is_all_you_need.pdf`，PDF第3页。

> Encoder: The encoder is composed of a stack of N = 6 identical layers.

- `attention_is_all_you_need.pdf`，PDF第3页。

> all sub-layers in the model, as well as the embedding layers, produce outputs of dimension dmodel = 512.

- `attention_is_all_you_need.pdf`，PDF第3页。

> Decoder: The decoder is also composed of a stack of N = 6 identical layers.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F19 《Video-LLaVA: Learning United Visual Representation by Alignment Before Projection》采用哪个语言模型？视觉编码器来自哪里并由什么模型初始化？训练时每个视频采样几帧？

参考答案：语言模型为Vicuna-7B v1.5；视觉编码器来自LanguageBind，并由OpenCLIP-L/14初始化；每个视频均匀采样8帧。

原文依据：

- `2311.10122v3.pdf`，PDF第5页。

> We employ Vicuna-7B v1.5 as the large language model. The visual encoders are derived from Lan- guageBind, initialized from OpenCLIP-L/14.

- `2311.10122v3.pdf`，PDF第5页。

> We uniformly sample 8 frames from each video,

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### F20 《How to Benchmark Vision Foundation Models for Semantic Segmentation?》的实验协议规定 ADE20K、PASCAL VOC、Cityscapes、GTA V 各训练多少步？有效 batch size 和随机种子重复次数是多少？

参考答案：ADE20K训练40,000步；PASCAL VOC、Cityscapes和GTA V各20,000步。实际batch size=1，通过梯度累积将有效batch size提至16；每个实验使用不同随机种子重复3次，报告均值与标准差。

原文依据：

- `Kerssies_How_to_Benchmark_Vision_Foundation_Models_for_Semantic_Segmentation_CVPRW_2024_paper.pdf`，PDF第5页。

> The batch size is set to 1 to make training more accessible by reducing the mem- ory requirements. Through gradient accumulation the effec- tive batch size is increased to 16 to align with Mask2Former. The number of training steps is set to 40,000 for ADE20K, and 20,000 for PASCAL VOC, Cityscapes and GTA V . Ex- periments are repeated thrice with different random seeds, and the average performance is reported along with the standard deviation.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

## 对比题

### C01 比较《Attention Is All You Need》和《An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale》：两篇论文如何把输入组织成序列，输出任务有何不同？请区分语言序列与图像块序列，并说明共同的注意力架构思路。

参考答案：要点：Transformer用于序列转换，以编码器—解码器和注意力处理输入、输出序列，原论文主要验证机器翻译。ViT将图像切为固定大小的块，进行线性嵌入、加位置嵌入后送入标准Transformer编码器，额外可学习分类token用于图像分类。二者共享序列表示和注意力思路，输入单元及输出任务不同，不能把ViT说成翻译解码器。

原文依据：

- `attention_is_all_you_need.pdf`，PDF第1页。

> We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.

- `attention_is_all_you_need.pdf`，PDF第1页。

> Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.

- `attention_is_all_you_need.pdf`，PDF第2页。

> Most competitive neural sequence transduction models have an encoder-decoder structure [5, 2, 35].

- `An_Image_is_Worth_16x16_Words.pdf`，PDF第3页。

> Model overview. We split an image into ﬁxed-size patches, linearly embed each of them, add position embeddings, and feed the resulting sequence of vectors to a standard Transformer encoder. In order to perform classiﬁcation, we use the standard approach of adding an extra learnable “classiﬁcation token” to the sequence.

可接受工具组合：`[["paper_compare"]]`

### C02 比较《Deep Residual Learning for Image Recognition》和《An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale》：两者改善视觉表征的核心机制和对数据规模的依赖有何差异？请说明残差连接、CNN视觉归纳偏置与ViT的大规模预训练思路。

参考答案：要点：ResNet以F(x)=H(x)-x重写残差映射，通过恒等shortcut将输入加到残差输出上，缓解更深网络的优化/退化问题。ViT的图像特定归纳偏置少于CNN；CNN内置局部性、二维邻域和平移等变性，而ViT更多从数据中学习空间关系，通常在大数据集预训练后迁移到较小下游任务。不能据此声称ResNet完全不需要训练数据，也不能脱离训练规模直接判定架构普遍优劣。

原文依据：

- `Deep_Residual_Learning_for_Image_Recognition.pdf`，PDF第2页。

> Formally, denoting the desired underlying mapping as H(x), we let the stacked nonlinear layers ﬁt another mapping of F(x): = H(x) − x. The orig- inal mapping is recast into F(x)+ x.

- `Deep_Residual_Learning_for_Image_Recognition.pdf`，PDF第2页。

> In our case, the shortcut connections simply perform identity mapping, and their outputs are added to the outputs of the stacked layers (Fig. 2).

- `An_Image_is_Worth_16x16_Words.pdf`，PDF第4页。

> We note that Vision Transformer has much less image-speciﬁc inductive bias than CNNs. In CNNs, locality, two-dimensional neighborhood structure, and translation equivariance are baked into each layer throughout the whole model.

- `An_Image_is_Worth_16x16_Words.pdf`，PDF第4页。

> Typically, we pre-train ViT on large datasets, and ﬁne-tune to (smaller) downstream tasks.

可接受工具组合：`[["paper_compare"]]`

### C03 比较《An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale》和《Vision Mamba: Efficient Visual Representation Learning with Bidirectional State Space Model》：二者都把图像分块后序列化，但如何获取全局上下文？在处理更长视觉序列时，核心计算机制的效率区别是什么？不要跨不同实验直接比较精度。

参考答案：要点：ViT把图像块嵌入送入标准Transformer编码器，通过自注意力建模块间关系。Vim使用位置嵌入和双向Mamba/状态空间模型压缩视觉表示，取得双向全局上下文。Vim论文的复杂度分析指出全局自注意力相对于序列长度为二次复杂度，SSM相对于序列长度为线性，因此面向长序列和高分辨率效率；理论复杂度应与具体硬件速度分开，不能跨基准精度/速度直接判优。

原文依据：

- `An_Image_is_Worth_16x16_Words.pdf`，PDF第3页。

> Model overview. We split an image into ﬁxed-size patches, linearly embed each of them, add position embeddings, and feed the resulting sequence of vectors to a standard Transformer encoder.

- `2401.09417v3.pdf`，PDF第1页。

> new generic vision backbone with bidirectional Mamba blocks (Vim), which marks the image sequences with position embeddings and com- presses the visual representation with bidirec- tional state space models.

- `2401.09417v3.pdf`，PDF第5页。

> where self-attention is quadratic to sequence length M, and SSM is linear to sequence length M (N is a fixed parameter, set to 16 by default).

可接受工具组合：`[["paper_compare"]]`

### C04 比较《Video-LLaVA: Learning United Visual Representation by Alignment Before Projection》和《A Thermal-Aware Infrared–Visible Image Fusion Method for Defect Detection in Power Transmission Equipment》：它们融合哪些输入信息、在哪一层完成对齐或交互、最终输出用于什么任务？请区分统一视觉—语言表征与红外—可见光图像融合。

参考答案：要点：Video-LLaVA用LanguageBind图像/视频编码器先对齐到共享语言特征空间，再使用共享投影层，把视觉表示和文本查询送入LLM生成语言回答。热感知方法用可见光和红外双分支分别提取结构纹理与热响应，以共享—特有表征及交互融合互补信息，以热感知门控强化热异常并保留结构，输出融合图像用于输电设备缺陷检测。二者输入模态、对齐空间及下游输出不同。

原文依据：

- `2311.10122v3.pdf`，PDF第4页。

> By shar- ing a language feature space, the image and video representations ultimately converge into a unified visual feature space, which we refer to as emergent alignment of images and videos. Therefore, our video encoder and image encoder are initialized from the LanguageBind encoders zoo, pre-aligning the inputs for LLM and reducing the gap between representations of different visual signals. The uni- fied visual representation is fed into LLM after passing through a shared projection layer.

- `2311.10122v3.pdf`，PDF第4页。

> Subsequently, the unified visual representation is encoded by shared projection layers, which is then combined with tokenized textual queries and fed into a large language model to generate correspond- ing responses.

- `energies-19-04788.pdf`，PDF第1页。

> The method employs separate visible and infrared branches to extract structural texture features and thermal response features, respectively. A shared– specific feature representation and interaction mechanism is then introduced to model visible-specific, infrared-specific, and cross-modal shared information, thereby improving complementary feature integration between the two modalities. In addition, a thermal- aware gated enhancement module adaptively strengthens salient thermal responses while preserving visible structural details.

可接受工具组合：`[["paper_compare"]]`

### C05 比较《How to choose a suitable method in image semantic segmentation-An Experimental Study》和《How to Benchmark Vision Foundation Models for Semantic Segmentation?》：两篇选型研究的实际实验数据、评价指标与基准建议有什么区别？为什么不能把前者的Top-K数值当成后者语义分割mIoU的直接替代？

参考答案：要点：Experimental Study虽讨论语义分割选型，但实际实验明确使用ILSVRC2012和Top-K类别准确率，比较六种CNN方法，多次运行取平均；该Top-K不是像素级分割质量。CVPRW研究分割微调、设置对排名和时间的影响，推荐ViT-B、16×16块、线性解码器及端到端微调，并采用多数据集，因为数据集和域偏移会影响排名；分割以预测/真值掩膜的mIoU评价。需区分实验口径，不可混用指标或直接比较数值判优。

原文依据：

- `How_to_Choose_a_Suitable_Method_in_Image_Semantic_Segmentation-An_Experimental_Study.pdf`，PDF第3页。

> The data sets used in this paper are the one used in ImageNet Large Scale Visual Recognition Challenge 2012 (ILSVRC2012).Top-K accuracy rate is used as an evaluation index,

- `How_to_Choose_a_Suitable_Method_in_Image_Semantic_Segmentation-An_Experimental_Study.pdf`，PDF第3页。

> Based on the data sets, experiments were conducted on all 6 methods, with each method running 5 times, and the average of the experimental results was taken as the final result.

- `Kerssies_How_to_Benchmark_Vision_Foundation_Models_for_Semantic_Segmentation_CVPRW_2024_paper.pdf`，PDF第8页。

> The results lead to a recommended benchmarking setup of fine- tuning the ViT-B variants of VFMs with a16×16 patch size and a linear decoder. Leveraging multiple datasets for train- ing and evaluation is also recommended, as the performance ranking across datasets and domain shifts varies. Linear probing is not recommended, as it is not representative of end-to-end fine-tuning.

- `Kerssies_How_to_Benchmark_Vision_Foundation_Models_for_Semantic_Segmentation_CVPRW_2024_paper.pdf`，PDF第4页。

> Following common practice, the mean intersection over union (mIoU) is used as the evaluation metric for seman- tic segmentation, which measures the overlap between pre- dicted and ground truth masks.

可接受工具组合：`[["paper_compare"]]`

### C06 比较《Zero-Shot Water Monitoring from Fixed Drainage Surveillance Imagery Across Day/Night and Rain/No-Rain Conditions: A SAM 3 Benchmark at 25 Urban Sites》和《How to Benchmark Vision Foundation Models for Semantic Segmentation?》：二者对基础模型采用了什么适配方式，验证目标有什么不同？如何理解水面监测中的零样本分割与语义分割基准中的监督微调建议？

参考答案：要点：水面监测用已有SAM 3及water提示做零样本分割，不做任务特定训练/标注来适配模型，提取水面积和水线指标，评价昼夜/雨情稳定性、事件检测、负样本误报及与专家掩膜的一致性。CVPRW基准考察VFM的语义分割监督微调，强调端到端微调的代表性，不推荐以线性探测替代它。特定水面场景零样本有效不表示通用多类分割无需微调；专家参考掩膜用于评价也不等于用于训练模型。

原文依据：

- `sensors-26-06403.pdf`，PDF第1页。

> This paper investigates whether a promptable segmentation founda‑ tion model can monitor water surfaces and waterlogging zero‑shot—without any task‑ specific training or labeling—across the full illumination–weather spectrum of real surveil‑ lance operations.

- `sensors-26-06403.pdf`，PDF第1页。

> Using SAM 3 with the text prompt “water”, we extract per‑frame water‑area ratio and normalized waterline level, and evaluate (i) quadrant‑wise segmenta‑ tion stability, (ii) rain‑event detection, (iii) false‑alarm behavior on negative days, and (iv) pixel‑level agreement with expert reference masks.

- `Kerssies_How_to_Benchmark_Vision_Foundation_Models_for_Semantic_Segmentation_CVPRW_2024_paper.pdf`，PDF第1页。

> Recent vision foundation models (VFMs) have demon- strated proficiency in various tasks but require supervised fine-tuning to perform the task of semantic segmentation ef- fectively.

- `Kerssies_How_to_Benchmark_Vision_Foundation_Models_for_Semantic_Segmentation_CVPRW_2024_paper.pdf`，PDF第8页。

> Linear probing is not recommended, as it is not representative of end-to-end fine-tuning.

可接受工具组合：`[["paper_compare"]]`

### C07 比较《SBRF-Det: Scale-Boundary Representative Fusion for Multi-Finding Detection in Panoramic Dental Radiographs》和《An Intelligent Framework for Tooth Segmentation and Classification Through Fusion of Transfer Learning with Advanced Optimization Algorithms Using Biomedical Images》：同样处理牙科影像，两者的预测对象、分割/检测流程与分类输出有什么区别？请说明SBRF-Det并非逐颗牙分类模型。

参考答案：要点：SBRF-Det检测全景牙科片中的多种病理、解剖和治疗相关发现，采用尺度相关代表分配和边界条件局部—全局特征的一阶段多发现检测，输出发现类别和定位。牙齿框架先用YOLO11s分割牙实例，再以DenseNet201、MobileNet、ShuffleNetV2提取并融合牙区特征，交给由BCO优化参数的KELM做32类牙齿分类。标注对象、任务链和类别含义不同，其检测mAP与分类accuracy不可直接相比。

原文依据：

- `diagnostics-16-03259.pdf`，PDF第1页。

> Panoramic dental radiographs frequently contain multiple coexisting patho- logical, anatomical, and treatment-related findings that vary in scale, contrast, and bound- ary definition.

- `diagnostics-16-03259.pdf`，PDF第1页。

> We propose SBRF-Det, a one-stage multi-finding detector integrating scale-dependent representative al- location with boundary-conditioned local–global feature fusion at P4/16.

- `oral-06-00131.pdf`，PDF第1页。

> Tooth instances are subsequently segmented using YOLO11s trained with the Adam optimizer. The segmented tooth regions are then processed through DenseNet201, MobileNet, and ShuffleNetV2 to obtain complementary deep feature representations, which are fused to construct a comprehensive feature representation. The fused features are classified using a Kernel Extreme Learning Machine (KELM), whose penalty parame- ter 𝐶 and RBF kernel parameter 𝛾 are optimized using Bacterial Colony Optimization (BCO).

- `oral-06-00131.pdf`，PDF第1页。

> dataset containing 598 images and 32 tooth classes.

可接受工具组合：`[["paper_compare"]]`

### C08 比较《Occlusion-Aware Watermelon Size Estimation Using YOLO11-OBB and Amodal GAN》和《Multi-View Semantic–Geometric Perception for Post-Disaster Flexible Suction with Metric 3D Scene Reconstruction》：两者都处理存在遮挡的场景，它们如何获得超出可见二维掩膜的信息？分别说明完整形状估计和具有物理尺度的三维场景重建。

参考答案：要点：西瓜方法针对可见区域分割在遮挡下低估果实大小的问题，结合YOLO11定位、椭圆建模与两阶段GAN做amodal完整形状估计，使用完整无遮挡果形和合成叶片遮挡训练。抽吸方案将同步多视角RGB、YOLO-LiteSeg障碍物掩膜与VGGT深度/相机参数结合，通过棋盘格对齐物理尺度，将二维语义投射到三维。前者恢复完整轮廓用于大小估计，后者提供有语义、物理尺度的高度/坡度/净空约束，不能互换。

原文依据：

- `engproc-159-00004.pdf`，PDF第1页。

> In addition, conventional detection and modal segmentation methods capture visible regions, resulting in systematic underestimation of fruit size under partial occlusion.

- `engproc-159-00004.pdf`，PDF第1页。

> developed in this study by integrating You Only Look Once 11-based localization, ellipse- based geometric modeling, and a two-stage generative adversarial network for instance segmentation. For effective learning, a reference dataset of full-shape watermelon images with ground-truth masks was constructed, and realistic synthetic occlusion was generated by overlaying leaf patches onto unoccluded fruits.

- `applsci-16-10003.pdf`，PDF第1页。

> YOLO-LiteSeg provides obstacle instance masks, while Visual Geometry Grounded Transformer (VGGT) provides depth and camera parameters for multi-view reconstruction; checkerboard-based metric alignment converts reconstruc- tion to physical scale. Projection-based 2D-to-3D semantic label transfer produces an ob- stacle-highlighted metric 3D scene representation for constraint-based suction-point se- lection.

可接受工具组合：`[["paper_compare"]]`

### C09 比较《Vision-Guided Cone Manipulation with Collaborative Robotic Arm》和《Multi-View Semantic–Geometric Perception for Post-Disaster Flexible Suction with Metric 3D Scene Reconstruction》：视觉感知如何接入机器人任务？两者在位置/尺度处理、动作选择和执行反馈方面分别提供了什么机制？

参考答案：要点：路锥系统在ROS2中使用YOLO位置、多次测量均值与初始/目标上方/必要时中间观察位姿改善定位，抓取前后负载差用于验证，失败可重试。抽吸方案用YOLO-LiteSeg和VGGT构建米制三维语义场景，以物理深度及障碍净空选择抽吸点。路锥研究含抓取反馈闭环，抽吸研究给出满足预设约束的选点参考；不能把感知/选点验证扩大为已完成完整灾后自主作业验证。

原文依据：

- `engproc-157-00021.pdf`，PDF第1页。

> The system operates within a ROS2-based frame- work and utilizes object position data provided by a YOLO-based vision subsystem. To improve localization accuracy, multiple measurements are collected and averaged before grasp planning. The grasping sequence is executed through predefined observation poses, including an initial detection position and a secondary pose above the target. When the cone is detected outside the optimal observation region, an additional intermediate obser- vation pose is generated to further reduce localization errors.

- `engproc-157-00021.pdf`，PDF第1页。

> Grasp reliability is enhanced through a weight-based validation method utilizing the collaborative robot’s built-in force sensing capability. The measured load before and after grasping is compared, and unsuc- cessful grasps automatically trigger up to three retry attempts.

- `applsci-16-10003.pdf`，PDF第1页。

> YOLO-LiteSeg provides obstacle instance masks, while Visual Geometry Grounded Transformer (VGGT) provides depth and camera parameters for multi-view reconstruction; checkerboard-based metric alignment converts reconstruc- tion to physical scale. Projection-based 2D-to-3D semantic label transfer produces an ob- stacle-highlighted metric 3D scene representation for constraint-based suction-point se- lection.

- `applsci-16-10003.pdf`，PDF第1页。

> The resulting 3D representation generated suction-point references satisfying predeﬁned suction-depth and obstacle-clearance criteria, providing metrically interpreta- ble spatial information for post-disaster ﬂexible suction.

可接受工具组合：`[["paper_compare"]]`

### C10 比较《Constructing a Xiangyunsha Defect Dataset and a Lightweight Detection Model for Sustainability》和《SBRF-Det: Scale-Boundary Representative Fusion for Multi-Finding Detection in Panoramic Dental Radiographs》：两项检测研究如何分离模型开发与最终评价，并验证结果稳定性？请比较留出集、随机种子和统计分析策略，避免跨数据集直接比较mAP。

参考答案：要点：香云纱研究分训练、验证、独立留出测试集，模型开发仅用训练/验证，按三个预定义种子的验证结果选架构，再报告对应独立训练的留出测试均值与标准差。SBRF-Det采用共同协议和固定留出队列，对A0–A2用三个独立种子，并进行成对影像级bootstrap差异分析。共同点是保留最终评价、检查稳定性；区别在选型过程与统计方法。数据和对象不同，mAP数值不能直接比较方法优劣。

原文依据：

- `sustainability-18-10291.pdf`，PDF第1页。

> In the revised experimental protocol, the dataset was divided into 1400 training, 331 validation, and 100 held‑out test images, with all model development experiments conducted using only the training and validation sub‑ sets. We compared a conventional five‑class taxonomy with a task‑oriented binary scheme and evaluated multiple YOLO26 model scales, architectural modifications, and two repre‑ sentative lightweight YOLO detectors. Based exclusively on the validation results across three predefined random seeds, YOLO26s‑DWR + DynamicConv was selected as the final modified architecture.

- `sustainability-18-10291.pdf`，PDF第1页。

> Across the three independently trained runs corresponding to seeds 0, 42, and 123, YOLO26s‑DWR + DynamicConv achieved a mean held‑out test mAP@0.5 of 46.1 ± 1.8%, compared with 39.8 ± 4.7% for the YOLO26s baseline.

- `diagnostics-16-03259.pdf`，PDF第1页。

> The method was evaluated on OralXrays-9, comprising 12,688 panoramic radiographs and 84,099 retained annotations across nine categories, using a fixed 2688-image hold-out cohort. Twenty-two detector configurations were compared under a common protocol, and A0–A2 were further assessed using three independent seeds and paired radiograph-level bootstrap analysis.

可接受工具组合：`[["paper_compare"]]`

### C11 比较《A Thermal-Aware Infrared–Visible Image Fusion Method for Defect Detection in Power Transmission Equipment》和《Constructing a Xiangyunsha Defect Dataset and a Lightweight Detection Model for Sustainability》：两者的缺陷识别结果最终如何服务实际决策？请比较输电设备热/结构异常检测与香云纱人工设计干预，并说明落地效果的表述边界。

参考答案：要点：热感知融合综合可见光结构缺陷与红外热异常，融合图像交给统一YOLO检测器服务设备缺陷识别，实验支持检测表征改善。香云纱将传统缺陷视作设计资源，定位结果支持工匠和设计者定向印染及局部裁切，是人主导决策支持。香云纱的定量节材、外部泛化和生命周期收益仍待验证；检测成绩不能直接表述为已证明减废效益或自主质量控制效果，二者业务目标不同。

原文依据：

- `energies-19-04788.pdf`，PDF第1页。

> Infrared and visible images provide complementary information for transmission equip- ment inspection, but a single modality is often insufficient to simultaneously represent structural defects and thermal abnormalities.

- `energies-19-04788.pdf`，PDF第1页。

> When the fused images are evaluated using a unified YOLO-based detector, the proposed thermal- aware fusion framework achieves precision, recall, and mAP at IoU = 0.5 values of 0.936, 0.921, and 0.943, respectively. These results indicate that the proposed thermal-aware fusion framework can effectively integrate visible structural information and infrared thermal response information and improve the recognition of transmission equipment defects in complex inspection scenarios.

- `sustainability-18-10291.pdf`，PDF第1页。

> Beyond detection, we further conducted a descriptive design case study in which localized Xiangyunsha surface irregularities informed human‑led design interventions, including targeted artistic print‑ ing/dyeing for textile_abnormal regions and localized pattern cutting for Stain_Patch re‑ gions. The resulting detection–interpretation–design intervention workflow positions AI as a decision support tool for artisans and designers rather than as an autonomous qual‑ ity control system. This study demonstrates the feasibility of linking defect localization with human‑led material‑retention strategies, while quantitative waste reduction, external generalizability, and lifecycle benefits remain to be established in future studies.

可接受工具组合：`[["paper_compare"]]`

### C12 比较《Occlusion-Aware Watermelon Size Estimation Using YOLO11-OBB and Amodal GAN》和《SBRF-Det: Scale-Boundary Representative Fusion for Multi-Finding Detection in Panoramic Dental Radiographs》：两者为何关注边界，改进边界的目的与方法有何不同？请区分遮挡下完整果形恢复和牙科多发现严格定位。

参考答案：要点：西瓜可见区域分割在遮挡下低估大小，方法用定位、椭圆建模、amodal GAN恢复完整形状，目标是完整轮廓和尺寸估计，报告IoU、Dice和边界F1。SBRF-Det针对不同尺度、低对比、弱边界的多种牙科发现，通过代表分配和边界条件局部—全局融合改善严格检测定位；收益有限且存在运行时权衡，部署前仍需临床等进一步验证。边界定义、任务和指标不同，边界F1与mAP不可直接比较胜负。

原文依据：

- `engproc-159-00004.pdf`，PDF第1页。

> In addition, conventional detection and modal segmentation methods capture visible regions, resulting in systematic underestimation of fruit size under partial occlusion.

- `engproc-159-00004.pdf`，PDF第1页。

> developed in this study by integrating You Only Look Once 11-based localization, ellipse- based geometric modeling, and a two-stage generative adversarial network for instance segmentation.

- `engproc-159-00004.pdf`，PDF第1页。

> segmentation performance with an intersection over union of 0.846, a dice of 0.915, and a boundary F1-score of 0.959.

- `diagnostics-16-03259.pdf`，PDF第1页。

> We propose SBRF-Det, a one-stage multi-finding detector integrating scale-dependent representative al- location with boundary-conditioned local–global feature fusion at P4/16.

- `diagnostics-16-03259.pdf`，PDF第1页。

> SBRF-Det improves strict localization through representative and boundary-aware feature modeling, but the gain is modest and introduces a runtime trade-off. Patient-linked, multi-center, and reader-centered validation remains necessary before clinical deployment.

可接受工具组合：`[["paper_compare"]]`

### C13 比较《Video-LLaVA: Learning United Visual Representation by Alignment Before Projection》和《Zero-Shot Water Monitoring from Fixed Drainage Surveillance Imagery Across Day/Night and Rain/No-Rain Conditions: A SAM 3 Benchmark at 25 Urban Sites》：两者都能接受文字，但文字在模型中的作用及训练方式有什么差异？请区分多模态指令调优与水面零样本文本提示。

参考答案：要点：Video-LLaVA混合图像/视频训练，先以视觉—文本对学习理解，再以含多轮对话的指令数据调优，后阶段LLM也参与训练，文字提出不同视觉理解任务并生成语言回答。水面方法使用已有SAM 3与固定water提示取得水面掩膜，不进行水面任务特定训练/标注来适配模型，继而计算水面积和水线。文字输入不意味着同样训练方式；水面零样本表示未做该任务微调，并非基础模型从未预训练。

原文依据：

- `2311.10122v3.pdf`，PDF第4页。

> We dynami- cally conduct joint training on images and videos, wherein a single batch contains both image and video samples simultaneously.

- `2311.10122v3.pdf`，PDF第4页。

> At this stage, the model is required to acquire the ability to interpret visual signals within an exten- sive image/video-text pair dataset. Each visual signal corresponds to a single round of conversa- tion data (Xq, Xa), where XT = Xq and Xa is the ground truth.

- `2311.10122v3.pdf`，PDF第4页。

> After this stage, the model learns to generate corresponding responses based on different instruc- tions and requests. The LLM are also involved in training at this stage.

- `sensors-26-06403.pdf`，PDF第1页。

> This paper investigates whether a promptable segmentation founda‑ tion model can monitor water surfaces and waterlogging zero‑shot—without any task‑ specific training or labeling—across the full illumination–weather spectrum of real surveil‑ lance operations.

- `sensors-26-06403.pdf`，PDF第1页。

> Using SAM 3 with the text prompt “water”, we extract per‑frame water‑area ratio and normalized waterline level,

可接受工具组合：`[["paper_compare"]]`

### C14 比较《Deep Residual Learning for Image Recognition》和《Vision Mamba: Efficient Visual Representation Learning with Bidirectional State Space Model》：两篇通用视觉骨干分别解决什么主要瓶颈？比较更深网络的优化问题与长视觉序列的计算/内存效率问题，并说明各自如何扩展到下游视觉任务。

参考答案：要点：ResNet针对更深网络的训练退化和优化困难，通过残差学习和shortcut使深层表征可训练，表征用于分类、检测、分割。Vim针对自注意力长视觉序列的速度/内存压力，使用双向状态空间模型取得上下文，先以ImageNet监督分类训练，再作为骨干迁移到语义分割、目标检测、实例分割。二者都有可迁移表征，但主要瓶颈与机制不同；骨干不等同无需任务头的端到端分割系统。

原文依据：

- `Deep_Residual_Learning_for_Image_Recognition.pdf`，PDF第1页。

> Deeper neural networks are more difﬁcult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously.

- `Deep_Residual_Learning_for_Image_Recognition.pdf`，PDF第1页。

> residual nets are foundations of our submissions to ILSVRC & COCO 2015 competitions 1, where we also won the 1st places on the tasks of ImageNet detection, ImageNet local- ization, COCO detection, and COCO segmentation.

- `2401.09417v3.pdf`，PDF第2页。

> subquadratic-time computation and linear memory complexity.

- `2401.09417v3.pdf`，PDF第2页。

> In the current stage, we train the Vim model on the supervised image classification task using the ImageNet dataset and then use the pretrained Vim as the backbone to perform sequential visual representation learning for downstream dense prediction tasks, i.e., semantic segmentation, object detection, and instance segmentation.

可接受工具组合：`[["paper_compare"]]`

### C15 比较《An Intelligent Framework for Tooth Segmentation and Classification Through Fusion of Transfer Learning with Advanced Optimization Algorithms Using Biomedical Images》和《A Thermal-Aware Infrared–Visible Image Fusion Method for Defect Detection in Power Transmission Equipment》：它们都采用特征融合，但融合的互补性来自哪里，融合后的分类/检测链条又有什么区别？

参考答案：要点：牙齿框架在同一牙科X光的分割牙区上，以DenseNet201、MobileNet、ShuffleNetV2提取互补深度特征并融合，由BCO调参的KELM进行牙类分类，互补性来自不同特征提取模型。热感知方法从可见光与红外两种输入提取结构纹理和热响应，融合共享/模态特有信息并进行热感知门控，融合图像用于YOLO缺陷检测，互补性来自传感模态。多模型特征融合不能说成红外—可见光双模态融合。

原文依据：

- `oral-06-00131.pdf`，PDF第1页。

> The segmented tooth regions are then processed through DenseNet201, MobileNet, and ShuffleNetV2 to obtain complementary deep feature representations, which are fused to construct a comprehensive feature representation. The fused features are classified using a Kernel Extreme Learning Machine (KELM), whose penalty parame- ter 𝐶 and RBF kernel parameter 𝛾 are optimized using Bacterial Colony Optimization (BCO).

- `energies-19-04788.pdf`，PDF第1页。

> The method employs separate visible and infrared branches to extract structural texture features and thermal response features, respectively. A shared– specific feature representation and interaction mechanism is then introduced to model visible-specific, infrared-specific, and cross-modal shared information, thereby improving complementary feature integration between the two modalities. In addition, a thermal- aware gated enhancement module adaptively strengthens salient thermal responses while preserving visible structural details.

- `energies-19-04788.pdf`，PDF第1页。

> When the fused images are evaluated using a unified YOLO-based detector, the proposed thermal- aware fusion framework achieves precision, recall, and mAP at IoU = 0.5 values of 0.936, 0.921, and 0.943, respectively.

可接受工具组合：`[["paper_compare"]]`

## 归纳题

### S01 请总结论文《Deep Residual Learning for Image Recognition》的研究问题、残差学习方法和主要实验结论。

参考答案：研究问题是增加网络深度时出现训练准确率退化，且该退化不只是过拟合。方法把目标映射H(x)改写为F(x)+x，让堆叠层学习F(x)=H(x)-x，并用恒等捷径连接相加。ImageNet和CIFAR-10实验表明残差网络更容易优化，增加深度可以带来准确率收益；论文的152层ImageNet模型复杂度仍低于VGG，残差网络集成取得3.57%的top-5测试错误率。

原文依据：

- `Deep_Residual_Learning_for_Image_Recognition.pdf`，PDF第1页。

> such degradation is not caused by overﬁtting , and adding more layers to a suitably deep model leads to higher train- ing error

- `Deep_Residual_Learning_for_Image_Recognition.pdf`，PDF第2页。

> Formally, denoting the desired underlying mapping as H(x), we let the stacked nonlinear layers ﬁt another mapping of F(x): = H(x) − x. The orig- inal mapping is recast into F(x)+ x.

- `Deep_Residual_Learning_for_Image_Recognition.pdf`，PDF第2页。

> We show that: 1) Our extremely deep residual nets are easy to optimize, but the counterpart “plain” nets (that simply stack layers) exhibit higher training error when the depth increases; 2) Our deep residual nets can easily enjoy accuracy gains from greatly increased depth, producing re- sults substantially better than previous networks.

- `Deep_Residual_Learning_for_Image_Recognition.pdf`，PDF第2页。

> Our 152- layer residual net is the deepest network ever presented on ImageNet, while still having lower complexity than VGG nets [40]. Our ensemble has 3.57% top-5 error on the ImageNet test set, and won the 1st place in the ILSVRC 2015 classiﬁcation competition .

可接受工具组合：`[["paper_summary"], ["knowledge_base_search"]]`

### S02 请总结论文《An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale》的图像输入表示、分类方法，以及预训练规模相关结论。

参考答案：ViT把图像切成固定大小patch并线性映射为嵌入，加入位置嵌入和可学习分类token后送入标准Transformer编码器，以分类token的输出进行图像分类。模型在较小规模数据上缺少CNN的局部性和平移等变性等归纳偏置，表现可能逊于同规模ResNet；足够大的预训练数据有助于弥补这一点，论文在ImageNet-21k/JFT-300M预训练后迁移到多个图像识别基准取得较强结果。

原文依据：

- `An_Image_is_Worth_16x16_Words.pdf`，PDF第3页。

> We split an image into ﬁxed-size patches, linearly embed each of them, add position embeddings, and feed the resulting sequence of vectors to a standard Transformer encoder. In order to perform classiﬁcation, we use the standard approach of adding an extra learnable “classiﬁcation token” to the sequence.

- `An_Image_is_Worth_16x16_Words.pdf`，PDF第2页。

> inherent to CNNs, such as translation equivariance and locality, and therefore do not generalize well when trained on insufﬁcient amounts of data. However, the picture changes if the models are trained on larger datasets (14M-300M images). We ﬁnd that large scale training trumps inductive bias. Our Vision Transformer (ViT) attains excellent results when pre-trained at sufﬁcient scale and transferred to tasks with fewer datapoints. When pre-trained on the public ImageNet-21k dataset or the in-house JFT-300M dataset, ViT approaches or beats state of the art on multiple image recognition benchmarks.

可接受工具组合：`[["paper_summary"], ["knowledge_base_search"]]`

### S03 请总结论文《Vision Mamba: Efficient Visual Representation Learning with Bidirectional State Space Model》的核心架构、视觉建模问题和评测任务。

参考答案：论文针对把Mamba用于视觉时的单向建模和位置感知不足，提出Vim：图像切patch并线性投影，加入位置嵌入，用双向选择性状态空间块进行依赖数据的全局视觉上下文建模。先在ImageNet监督图像分类上训练，再将骨干用于语义分割、目标检测和实例分割。状态空间计算随序列长度线性增长，与全局自注意力的二次增长形成效率差异；论文报告的优势应限定在其任务、模型和实验设置内。

原文依据：

- `2401.09417v3.pdf`，PDF第2页。

> However, there are two challenges for Mamba, i.e., unidi- rectional modeling and lack of positional awareness. To address these challenges, we propose the Vision Mamba (Vim) model, which incorporates the bidirectional SSMs for data-dependent global visual context modeling and position embeddings for location-aware visual recognition.

- `2401.09417v3.pdf`，PDF第2页。

> We first split the input image into patches and linearly project them as vectors to Vim. Image patches are treated as the sequence data in Vim blocks, which efficiently compresses the vi- sual representation with the proposed bidirectional selective state space.

- `2401.09417v3.pdf`，PDF第2页。

> In the current stage, we train the Vim model on the supervised image classification task using the ImageNet dataset and then use the pretrained Vim as the backbone to perform sequential visual representation learning for downstream dense prediction tasks, i.e., semantic segmentation, object detection, and instance segmentation.

- `2401.09417v3.pdf`，PDF第5页。

> where self-attention is quadratic to sequence length M, and SSM is linear to sequence length M (N is a fixed parameter, set to 16 by default).

可接受工具组合：`[["paper_summary"], ["knowledge_base_search"]]`

### S04 请总结论文《Video-LLaVA: Learning United Visual Representation by Alignment Before Projection》的统一视觉表示方法和训练流程。

参考答案：Video-LLaVA使用LanguageBind图像与视频编码器，使两种视觉表示在投影前对齐到共同的语言特征空间，再经共享投影层与文本token组合送入大语言模型。联合训练的单个batch同时含图像和视频样本；训练包括视觉理解训练和指令微调。前一阶段以自回归目标学习基本视觉理解并冻结其他参数；后一阶段要求响应更复杂的视觉理解指令，LLM也参与训练，最后按不同指令和请求生成回答。

原文依据：

- `2311.10122v3.pdf`，PDF第4页。

> Therefore, our video encoder and image encoder are initialized from the LanguageBind encoders zoo, pre-aligning the inputs for LLM and reducing the gap between representations of different visual signals. The uni- fied visual representation is fed into LLM after passing through a shared projection layer.

- `2311.10122v3.pdf`，PDF第4页。

> We dynami- cally conduct joint training on images and videos, wherein a single batch contains both image and video samples simultaneously.

- `2311.10122v3.pdf`，PDF第4页。

> The training objective of this stage is the original auto-regressive loss, where the model learns the basic ability to view the vision. We freeze the other parameters of the model during this process.

- `2311.10122v3.pdf`，PDF第4页。

> In this stage, the model is required to provide responses corresponding to different instructions. These instructions often involve more complex visual comprehension tasks, rather than just de- scribing visual signals.

- `2311.10122v3.pdf`，PDF第4页。

> After this stage, the model learns to generate corresponding responses based on different instruc- tions and requests. The LLM are also involved in training at this stage.

可接受工具组合：`[["paper_summary"], ["knowledge_base_search"]]`

### S05 请总结论文《How to Benchmark Vision Foundation Models for Semantic Segmentation?》推荐的评测配置、数据集使用方式和不推荐的做法。

参考答案：论文研究如何兼顾排名代表性与训练效率。推荐使用ViT-B、16×16 patch、线性解码器进行端到端微调；这组配置相对于更大模型、更强解码器和更小patch的配置，能够大幅减少训练时间并具有一定排名代表性。建议使用多个数据集进行训练和评估，因为数据集和域偏移会改变模型排名。论文不推荐仅做线性探测，因为冻结编码器得到的排名不能代表端到端微调。

原文依据：

- `Kerssies_How_to_Benchmark_Vision_Foundation_Models_for_Semantic_Segmentation_CVPRW_2024_paper.pdf`，PDF第1页。

> Based on the results, the recommendation is to fine- tune the ViT-B variants of VFMs with a 16 × 16 patch size and a linear decoder, as these settings are representative of using a larger model, more advanced decoder and smaller patch size, while reducing training time by more than 13 times.

- `Kerssies_How_to_Benchmark_Vision_Foundation_Models_for_Semantic_Segmentation_CVPRW_2024_paper.pdf`，PDF第8页。

> Leveraging multiple datasets for train- ing and evaluation is also recommended, as the performance ranking across datasets and domain shifts varies. Linear probing is not recommended, as it is not representative of end-to-end fine-tuning.

可接受工具组合：`[["paper_summary"], ["knowledge_base_search"]]`

### S06 请总结论文《How to choose a suitable method in image semantic segmentation-An Experimental Study》实际比较的六种方法、实验数据与评价指标、主要结果。

参考答案：实际比较DenseNet201、EfficientNetB7、InceptionV3、ResNet152V2、InceptionResNetV2和VGG16。第4节使用ILSVRC2012数据，以Top-K准确率评估，每种方法运行5次取平均。结果是EfficientNetB7在Top1最好，ResNet152V2在Top2、Top3最好；这两种方法的Top3均超过0.8。尽管题名讨论语义分割，文中该实验报告的是图像类别Top-K指标，不能把它直接当作像素级分割mIoU。

原文依据：

- `How_to_Choose_a_Suitable_Method_in_Image_Semantic_Segmentation-An_Experimental_Study.pdf`，PDF第3页。

> The data sets used in this paper are the one used in ImageNet Large Scale Visual Recognition Challenge 2012 (ILSVRC2012).Top-K accuracy rate is used as an evaluation index

- `How_to_Choose_a_Suitable_Method_in_Image_Semantic_Segmentation-An_Experimental_Study.pdf`，PDF第1页。

> specifically six methods including DenseNet201, EfficientNetB7, InceptionResNetV2, InceptionV3, ResNet152V2 and VGG16.

- `How_to_Choose_a_Suitable_Method_in_Image_Semantic_Segmentation-An_Experimental_Study.pdf`，PDF第3页。

> Based on the data sets, experiments were conducted on all 6 methods, with each method running 5 times, and the average of the experimental results was taken as the final result.

- `How_to_Choose_a_Suitable_Method_in_Image_Semantic_Segmentation-An_Experimental_Study.pdf`，PDF第4页。

> As shown in the figure, EfficientNetB7 performs best in Top1 accuracy, but is surpassed by ResNet152V2 in Top2 and Top3 accuracies. Although DenseNet201 has lower accuracy in Top 1 compared to other methods, its performance on Top2 and Top 3 is similar to those of InceptionV3 and VGG16. In summary, EfficientNetB7 and ResNet152V2 perform well, the Top3 accuracy both exceeding 0.8

可接受工具组合：`[["paper_summary"], ["knowledge_base_search"]]`

### S07 请总结论文《Multi-View Semantic–Geometric Perception for Post-Disaster Flexible Suction with Metric 3D Scene Reconstruction》的输入、三个处理模块和输出。

参考答案：输入为机械臂相机采集的同步多视角RGB图像。三个模块为轻量障碍物实例分割、具有物理尺度的3D场景重建、带约束的吸取点选择。YOLO-LiteSeg生成语义实例掩码，VGGT预测相机参数与深度并重建场景，之后进行尺度对齐，将2D障碍物标签投影到3D点云。输出为满足预设吸取深度与最大化最小障碍物间距准则的吸取点参考；该参考不等于完整吸取轨迹或过程的全局最优方案。

原文依据：

- `applsci-16-10003.pdf`，PDF第4页。

> The framework takes synchronized RGB im- age sequences acquired from multiple arm-mounted camera positions as input and com- prises three coupled modules: lightweight obstacle instance segmentation, metric 3D scene reconstruction, and constraint-based suction-point selection.

- `applsci-16-10003.pdf`，PDF第4页。

> YOLO-LiteSeg gener- ates class-labeled 2D instance masks that provide semantic cues for subsequent projection- based 2D-to-3D semantic label transfer, while VGGT independently predicts camera pa- rameters and dense depth from the RGB images for multi-view reconstruction, followed by metric alignment of the reconstructed scene.

- `applsci-16-10003.pdf`，PDF第4页。

> Finally, semantic labels from the 2D obstacle instance masks are transferred to the corresponding reconstructed 3D points, and the resulting metric 3D scene representation integrating obstacle semantics and reconstructed geometry is converted into a suction-point reference using the target suction-depth criterion and the maximin obstacle-clearance criterion.

- `applsci-16-10003.pdf`，PDF第4页。

> yielding a selected suction-point reference rather than a global optimum for the complete suction trajectory or process.

可接受工具组合：`[["paper_summary"], ["knowledge_base_search"]]`

### S08 请总结论文《An Intelligent Framework for Tooth Segmentation and Classification Through Fusion of Transfer Learning with Advanced Optimization Algorithms Using Biomedical Images》的主要处理链与评测对象。

参考答案：TSCFFM-AOABI先用Blur、MedianBlur、ToGray和CLAHE增强图像，再用Adam训练的YOLO11s分割牙齿实例。DenseNet201、MobileNet和ShuffleNetV2提取分割区域的互补特征并融合，由KELM分类，BCO优化KELM惩罚参数C和RBF核参数γ。论文使用包含598张牙科X光图像与32类牙齿的基准集，报告准确率96.17%、精确率95.10%、召回率99.03%和F1 98.00%；这些是该数据集实验报告，不能直接等同于临床部署效果。

原文依据：

- `oral-06-00131.pdf`，PDF第1页。

> Methods: The proposed frame work first applies image augmentation using Blur, MedianBlur, ToGray, and Contrast -Limited Adaptive Histogram Equalization (CLAHE) to improve image variability and feature vis- ibility. Tooth instances are subsequently segmented using YOLO11s trained with the Adam optimizer.

- `oral-06-00131.pdf`，PDF第1页。

> The segmented tooth regions are then processed through DenseNet201, MobileNet, and ShuffleNetV2 to obtain complementary deep feature representations, which are fused to construct a comprehensive feature representation. The fused features are classified using a Kernel Extreme Learning Machine (KELM), whose penalty parame- ter 𝐶 and RBF kernel parameter 𝛾 are optimized using Bacterial Colony Optimization (BCO).

- `oral-06-00131.pdf`，PDF第1页。

> Results: The proposed framework is evaluated on a benchmark dental X-ray image dataset containing 598 images and 32 tooth classes. Experimental results demonstrate an accuracy of 96.17%, precision of 95.10%, recall of 99.03%, and an F1-score of 98.00%.

可接受工具组合：`[["paper_summary"], ["knowledge_base_search"]]`

### S09 结合论文《Vision-Guided Cone Manipulation with Collaborative Robotic Arm》和《Occlusion-Aware Watermelon Size Estimation Using YOLO11-OBB and Amodal GAN》，归纳两项工作如何把视觉感知结果转化为下游任务所需的信息。

参考答案：交通锥抓取工作利用YOLO和双目视觉估计位置，通过50次观测平均和多阶段观测提高抓取坐标准确性，再结合机械臂的载荷变化验证抓取。西瓜工作利用YOLO11-OBB进行旋转目标定位，把定向边界框转换为椭圆几何先验，指导AISGAN完成被遮挡部分的非模态重建，并通过双椭圆等后处理得到更完整的形状用于尺寸估计。共同点是视觉模型之后均加入与任务有关的几何或验证环节，不能只凭原始检测输出完成下游任务。

原文依据：

- `engproc-157-00021.pdf`，PDF第5页。

> The vision subsystem combines deep-learning-based object detection with stereo vision to estimate traffic cone positions relative to the camera coordinate system.

- `engproc-157-00021.pdf`，PDF第5页。

> For this the cone collector program collects 50 consecutive measurements and calcu- lates their average. The experiment results showed that this number is a balance between fast execution and high accuracy.

- `engproc-157-00021.pdf`，PDF第5页。

> The combination of point averaging and multi-stage observation provides sufficient positioning accuracy for reliable cone grasping.

- `engproc-157-00021.pdf`，PDF第3页。

> The system utilizes the collaborative features of the robot arm by measuring the load applied to the end-effector before and after the grasping operation, allowing automatic validation of a successful cone grasp.

- `engproc-159-00004.pdf`，PDF第3页。

> YOLO11-OBB is used to provide rotation-aware localization for inference in this study. The oriented bounding boxes are converted into ellipse-based geometric priors that guide AISGAN amodal reconstruction and improve robustness under arbitrary fruit orientation.

- `engproc-159-00004.pdf`，PDF第5页。

> This dual-ellipse strategy is used to enhance robustness under asymmetric occlusion by capturing alternative boundary interpretations and reducing underestimation. Figure 5c shows this process, where two ellipses are generated from different minor-axis points and merged to form the final reconstructed shape.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### S10 结合《A Thermal-Aware Infrared–Visible Image Fusion Method for Defect Detection in Power Transmission Equipment》《Zero-Shot Water Monitoring from Fixed Drainage Surveillance Imagery Across Day/Night and Rain/No-Rain Conditions: A SAM 3 Benchmark at 25 Urban Sites》和《Constructing a Xiangyunsha Defect Dataset and a Lightweight Detection Model for Sustainability》，分别归纳视觉输入、主要方法和最终任务输出。

参考答案：输电设备论文使用配准的可见光与红外图像，采用双流结构、共享/专属特征交互与热感知门控融合，得到融合表示并供YOLO检测结构和热异常。排水监控论文输入固定监控摄像头图像，以SAM 3及water文本提示进行零样本分割，提取水面积比例与归一化水线，结合规则进行降雨/积水事件与误报分析。香云纱论文构建1831张缺陷图像的数据集，验证集选择YOLO26s-DWR + DynamicConv，用缺陷位置支持人工设计干预；其流程是设计决策支持，量化减废和生命周期收益仍待验证。

原文依据：

- `energies-19-04788.pdf`，PDF第1页。

> The method employs separate visible and infrared branches to extract structural texture features and thermal response features, respectively. A shared– specific feature representation and interaction mechanism is then introduced to model visible-specific, infrared-specific, and cross-modal shared information, thereby improving complementary feature integration between the two modalities. In addition, a thermal- aware gated enhancement module adaptively strengthens salient thermal responses while preserving visible structural details.

- `energies-19-04788.pdf`，PDF第1页。

> Experiments are conducted on a spatially aligned infrared–visible dataset containing normal insulator strings, normal strain clamps, damaged insulator strings, insulator thermal faults, and strain clamp thermal faults.

- `sensors-26-06403.pdf`，PDF第1页。

> Using SAM 3 with the text prompt “water”, we extract per‑frame water‑area ratio and normalized waterline level, and evaluate (i) quadrant‑wise segmenta‑ tion stability, (ii) rain‑event detection, (iii) false‑alarm behavior on negative days, and (iv) pixel‑level agreement with expert reference masks.

- `sustainability-18-10291.pdf`，PDF第1页。

> we constructed a specialized Xiangyunsha defect‑image dataset comprising 1831 annotated images.

- `sustainability-18-10291.pdf`，PDF第1页。

> Based exclusively on the validation results across three predefined random seeds, YOLO26s‑DWR + DynamicConv was selected as the final modified architecture.

- `sustainability-18-10291.pdf`，PDF第1页。

> The resulting detection–interpretation–design intervention workflow positions AI as a decision support tool for artisans and designers rather than as an autonomous qual‑ ity control system. This study demonstrates the feasibility of linking defect localization with human‑led material‑retention strategies, while quantitative waste reduction, external generalizability, and lifecycle benefits remain to be established in future studies.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

## 推理题

### R01 论文《Attention Is All You Need》为什么在点积注意力中除以sqrt(d_k)？请按正文给出的解释回答。

参考答案：正文指出d_k较大时，点积幅度会变大，可能把softmax推入梯度极小的区域，影响训练。因此按1/sqrt(d_k)缩放点积以抵消该效应。脚注用分量独立、均值0、方差1的假设说明点积方差为d_k；这是该说明的假设条件。

原文依据：

- `attention_is_all_you_need.pdf`，PDF第4页。

> We suspect that for large values of dk, the dot products grow large in magnitude, pushing the softmax function into regions where it has extremely small gradients 4. To counteract this effect, we scale the dot products by 1√dk .

- `attention_is_all_you_need.pdf`，PDF第4页。

> assume that the components of q and k are independent random variables with mean 0 and variance 1. Then their dot product, q · k = Pdk i=1 qiki, has mean 0 and variance dk.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### R02 根据《An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale》，为什么不能仅根据ImageNet上从头训练的表现否定ViT？请结合归纳偏置和预训练规模的实验讨论。

参考答案：ViT缺少CNN的局部性和平移等变性等归纳偏置，数据不足时泛化会受到影响；这说明小数据训练结果依赖数据规模，不能直接否定该架构。论文在更大预训练集上看到更强结果：ViT-Large在ImageNet预训练下不如ViT-Base，ImageNet-21k下相近，JFT-300M下才显现大模型的完整收益。该结论限定于论文的模型与实验，不能推成任意数据规模下ViT都优于CNN。

原文依据：

- `An_Image_is_Worth_16x16_Words.pdf`，PDF第2页。

> inherent to CNNs, such as translation equivariance and locality, and therefore do not generalize well when trained on insufﬁcient amounts of data. However, the picture changes if the models are trained on larger datasets (14M-300M images). We ﬁnd that large scale training trumps inductive bias.

- `An_Image_is_Worth_16x16_Words.pdf`，PDF第6页。

> When pre-trained on the smallest dataset, ImageNet, ViT-Large models underperform compared to ViT-Base models, despite (moderate) regularization. With ImageNet-21k pre-training, their performances are similar. Only with JFT-300M, do we see the full beneﬁt of larger models.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### R03 论文《Vision Mamba: Efficient Visual Representation Learning with Bidirectional State Space Model》为什么同时引入双向SSM和位置嵌入？它们分别处理什么问题？

参考答案：论文将原始Mamba用于视觉的困难概括为单向建模和缺乏位置感知。双向SSM用于依赖数据的全局视觉上下文建模；位置嵌入为视觉识别提供位置信息，在密集预测中体现空间感知。它们是不同问题的对应设计，不能把双向性理解为代替位置信息。

原文依据：

- `2401.09417v3.pdf`，PDF第2页。

> However, there are two challenges for Mamba, i.e., unidi- rectional modeling and lack of positional awareness. To address these challenges, we propose the Vision Mamba (Vim) model, which incorporates the bidirectional SSMs for data-dependent global visual context modeling and position embeddings for location-aware visual recognition.

- `2401.09417v3.pdf`，PDF第2页。

> Furthermore, the position embedding in Vim block provides the awareness for spatial information, which enables Vim to be more robust in dense prediction tasks.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### R04 根据《How to Benchmark Vision Foundation Models for Semantic Segmentation?》，为什么线性探测更省训练资源却仍不被推荐作为端到端微调的替代评测？

参考答案：冻结编码器会改变不同VFM的表现与排名，论文得到的排名相关系数仅0.38。因此线性探测虽然减少训练成本，却不足以代表端到端微调的结果；作者建议使用端到端微调来获得有代表性的比较。

原文依据：

- `Kerssies_How_to_Benchmark_Vision_Foundation_Models_for_Semantic_Segmentation_CVPRW_2024_paper.pdf`，PDF第5页。

> Current VFMs may not acquire enough spatial semantic understanding in pretraining to perform semantic segmentation effectively without end-to-end fine-tuning. Furthermore, a low correla- tion coefficient of 0.38 suggests freezing the encoder signif- icantly changes the performance ranking. Therefore, even though linear probing is efficient, end-to-end fine-tuning is recommended for a representative benchmark.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### R05 根据《SBRF-Det: Scale-Boundary Representative Fusion for Multi-Finding Detection in Panoramic Dental Radiographs》，为什么边界相关局部信息对mAP50-95比仅正确分类更关键？请结合正文中的局部与全局融合解释。

参考答案：mAP50-95要求在逐渐严格的IoU阈值下仍有准确边界框重叠，正确类别本身不足以获得较高指标。局部信息保留病灶边缘、修复体界面、牙根等结构线索，可以影响框几何；全局上下文帮助区分外观相似而解剖位置不同的发现。边界门控对局部分支增强调节更强、对全局分支仅适度衰减，以兼顾边界定位与语义上下文。

原文依据：

- `diagnostics-16-03259.pdf`，PDF第15页。

> A strong boundary response increases the local contribution while only moderately attenuating the global branch.

- `diagnostics-16-03259.pdf`，PDF第15页。

> Global context helps distinguish visually similar structures that occur in different anatomical settings, while local evidence is retained around lesion margins, restoration interfaces, root struc- tures, and other high-frequency regions. The P4 placement further preserves a spatial resolution at which these cues can influence box geometry. This design is particularly relevant to mAP50-95, where correct class prediction alone is insufficient and bounding-box overlap must remain accurate across progressively stricter IoU thresholds.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### R06 根据《A Thermal-Aware Infrared–Visible Image Fusion Method for Defect Detection in Power Transmission Equipment》，为什么可见光与红外需要互补融合，而简单平均仍有局限？

参考答案：可见光提供轮廓、纹理与结构异常，但受光照、背景和遮挡影响；红外能揭示异常发热，却缺少丰富纹理且结构边界模糊。简单平均能加入两种信息，但平等对待所有模态和位置，不考虑模态特性、空间重要性与热响应分布。论文因此采用热感知门控和共享/专属特征交互；在该文同协议检测对比中，提出方法的mAP@0.5:0.95为0.657，简单平均为0.597，不能把该结果外推到所有融合任务。

原文依据：

- `energies-19-04788.pdf`，PDF第2页。

> Visible images provide rich appear- ance, contour, and texture information and are therefore suitable for identifying structural abnormalities such as damage, cracks, deformation, and foreign object attachment. Infrared images provide complementary thermal response information and are particularly use- ful for revealing abnormal heating associated with poor contact, insulation degradation, and other thermally related faults. However, visible images are sensitive to illumination, background interference, and occlusion, whereas infrared images generally provide limited texture details and relatively blurred structural boundaries [4].

- `energies-19-04788.pdf`，PDF第48页。

> However, simple averaging treats visible and infrared information equally and does not consider modality-specific characteristics, spatial importance, or thermal response distribution. The proposed fused representation achieves precision, recall, and mAP at IoU = 0.5 values of 0.936, 0.921, and 0.943, respectively. Compared with simple average fusion, the proposed framework improves mAP at IoU = 0.5:0.95 from 0.597 to 0.657, corresponding to an absolute improvement of 0.060.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### R07 论文《Constructing a Xiangyunsha Defect Dataset and a Lightweight Detection Model for Sustainability》为什么把测试集排除在模型选择之外，并在修订划分后从头训练模型？

参考答案：测试集只在最终结构选择后用于最终评估，训练集用于优化，验证集用于模型规模比较、消融和选择，从而避免把模型开发用过的数据当作独立最终评测。修订协议下从头训练且不继承旧实验的权重、检查点、优化器状态或其他学习状态，避免旧实验状态影响新划分。作者明确说该协议分离开发与保留集评估，并降低把验证表现报告成最终模型表现的评价偏差。

原文依据：

- `sustainability-18-10291.pdf`，PDF第5页。

> The training set was used for model optimization, while the validation set was used for model‑scale comparison, architectural ablation, and final model selection. The 100‑image held‑out test set was excluded from all model‑development decisions and was used only after the final architecture had been selected. All models reported under this revised protocol were trained from scratch using the revised data partition, without inheriting checkpoints, model weights, optimizer states, or other learned states from the experiments reported in the original submission.

- `sustainability-18-10291.pdf`，PDF第5页。

> This revised protocol separates model development from final held‑out evaluation and reduces the evaluation bias associated with reporting validation‑set performance as final model performance.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### R08 论文《Zero-Shot Water Monitoring from Fixed Drainage Surveillance Imagery Across Day/Night and Rain/No-Rain Conditions: A SAM 3 Benchmark at 25 Urban Sites》为什么不把复合报警规则在102个负例帧上的0误报直接称为已验证误报率？它如何进一步评估？

参考答案：规则与阈值来自同一批负例数据，因此0/102是回顾性、样本内的一致性结果，缺少独立前瞻验证。随后作者冻结SAM 3、water提示、0.25置信度和报警规则，在未参与阈值或规则设计的额外14天1072帧上不再调参运行。文中观察到的六个前瞻误报都是单帧模式切换瞬态，两帧持续条件是在观察这些失败后提出的后验加固，不能与原冻结规则的独立验证混为一谈。

原文依据：

- `sensors-26-06403.pdf`，PDF第8页。

> Both rules and the threshold were designed from the negative‑day data reported in Section 5.3, to which the 4 September day belongs; the alarm evaluation there is therefore retrospective and in‑sample, and its zero‑alarm out‑ come should be read as a consistency demonstration rather than an independent prospec‑ tive validation.

- `sensors-26-06403.pdf`，PDF第11页。

> selected 14 additional days at the reference site that had never been used for threshold or rule design: seven days with event‑triggered 5‑min capture (11/12/13/14 August 2026, 31 August, 1 September, 17 September) and seven routine hourly capture days (24/25/27 August 2026, 8/10/13/15 September), totaling 1072 frames. The pipeline (SAM 3, prompt “water”, confidence 0.25) and both alarm rules were applied exactly as frozen in Sections 4.1–4.3, without any re‑tuning.

- `sensors-26-06403.pdf`，PDF第12页。

> A minimal post hoc hardening. Because all six prospective false alarms were single‑ frame transients at mode switchover, we evaluated the simplest possible remedy, decided only after inspecting these failures: require the alarm condition to hold on at least two con‑ secutive frames (at 5‑min sampling, a 10‑min persistence; at hourly sampling, two adjacent hours).

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### R09 根据《Multi-View Semantic–Geometric Perception for Post-Disaster Flexible Suction with Metric 3D Scene Reconstruction》，为什么仅有2D实例掩码或未对齐物理尺度的3D重建不足以支持吸取点选择？

参考答案：2D掩码提供障碍物语义，但不能直接给出物理高度、坡度或障碍物间距。吸取深度、沉积厚度、距离等是有单位的量，未定尺度的重建不能直接应用这些约束。论文将YOLO-LiteSeg语义与VGGT几何结合，用棋盘格对齐到物理尺度并将2D标签转到3D点云，在吸取深度和最大化最小障碍物间距准则下生成参考点。

原文依据：

- `applsci-16-10003.pdf`，PDF第1页。

> image-plane masks alone cannot provide physical height, surface slope, or obstacle clearance, while geometry with- out semantics cannot distinguish obstacle regions from obstacle-free sludge regions.

- `applsci-16-10003.pdf`，PDF第2页。

> For ﬂexible suction, the reconstructed geometry must addi- tionally be converted to physical scale because sludge-deposit thickness, height proﬁles, obstacle distances, and suction depth are metric quantities rather than scale-ambiguous geometric descriptors.

- `applsci-16-10003.pdf`，PDF第4页。

> Finally, semantic labels from the 2D obstacle instance masks are transferred to the corresponding reconstructed 3D points, and the resulting metric 3D scene representation integrating obstacle semantics and reconstructed geometry is converted into a suction-point reference using the target suction-depth criterion and the maximin obstacle-clearance criterion.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`

### R10 论文《Occlusion-Aware Watermelon Size Estimation Using YOLO11-OBB and Amodal GAN》为什么需要非模态分割与椭圆先验，而不只使用可见区域分割？

参考答案：普通可见区域分割会在遮挡时产生不完整掩码，导致尺寸低估。论文用AISGAN重建完整水果几何；YOLO11-OBB输出旋转感知位置并转换为椭圆先验，引导非模态重建应对不同方向。双椭圆后处理结合两种边界解释，在不对称遮挡下提高形状补全的稳健性、减少低估。

原文依据：

- `engproc-159-00004.pdf`，PDF第2页。

> Watermelons are often occluded, causing incomplete masks and underestimated size.

- `engproc-159-00004.pdf`，PDF第3页。

> The oriented bounding boxes are converted into ellipse-based geometric priors that guide AISGAN amodal reconstruction and improve robustness under arbitrary fruit orientation.

- `engproc-159-00004.pdf`，PDF第5页。

> This dual-ellipse strategy is used to enhance robustness under asymmetric occlusion by capturing alternative boundary interpretations and reducing underestimation. Figure 5c shows this process, where two ellipses are generated from different minor-axis points and merged to form the final reconstructed shape.

可接受工具组合：`[["knowledge_base_search"], ["knowledge_base_retrieve"], ["knowledge_base_retrieve", "knowledge_base_search"]]`
