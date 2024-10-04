# Agent-Based Single Cryptocurrency Trading Challenge - FinNLP-FNP-LLMFinLegal @ COLING-2025

## Usage

In this section, we provide a step-by-step guide to running the evaluation framework with the fine-tuned LLM. The evaluation framework consists of three parts:

- **VLLM Server**: The server that provides the API for the fine-tuned LLM. We will use the Docker image provided by the VLLM team. We will explore how to deploy both a LLM and a base LLM with a LoRA head.

- **Qdrant Vector Database**: We will use Qdrant as the vector database for memory storage.

- **FinMem Framework**: After deploying the VLLM server and Qdrant vector database, we will demonstrate how to run the evaluation framework to assess trading performance.

### Credentials

The credentials need to be saved in the [.env](/.env) file. The `.env` file should contain the following information:

```bash
OPENAI_API_KEY=XXXXXX-XXXXXX-XXXXXX-XXXXXX-XXXXXX
HUGGING_FACE_HUB_TOKEN=XXXXXX-XXXXXX-XXXXXX-XXXXXX-XXXXXX
```

The OpenAI API key is used to generate the embeddings for input text. The Hugging Face Hub token is used to download the fine-tuned LLM model.  Please make sure the Hugging Face Hub token has the access to the fine-tuned LLM model/LORA head.

### Config

The configuration in the project is managed by [Pkl](<https://pkl-lang.org/index.html>). The configurations are spited into two parts: [chat models](</configs/chat_models.pkl>) and [meta config](</configs/main.pkl>).

#### Chat Config

##### Deploying LLM

To deploy a fine-tuned / merged LLM model, please add an entry in the [configs/chat_models.pkl](</configs/chat_models.pkl>) that follows the following format:

```pkl
llama3_1_instruct_8b: ChatModelConfig = new {  # set the identifier for the model
    chat_model = "meta-llama/Meta-Llama-3.1-8B-Instruct" # set the model name, which is the model path in the Hugging Face Hub
    chat_model_type = "instruction"  # set the model type, which should be one of the following: instruction, chat, completion. 
    # The completion model type is the similar to meta-llama/Llama-3.1-8B that generates the completion for the input text.
    chat_model_inference_engine = "vllm"  # keep it as vllm
    chat_endpoint = null  # keep it null
    chat_template_path = null  # please see detail in VLLM doc: https://github.com/vllm-project/vllm/blob/main/docs/source/serving/openai_compatible_server.md#chat-template
    chat_system_message = "You are a helpful assistant."
    chat_parameters = new Mapping {} # leave it as empty
  }
```

After adding the entry, the model is also needed to be added in the registry.

```pkl
chat_model_dict = new Mapping {
    ["llama-3.1-8b-instruct"] = llama3_1_instruct_8b # [<a short name>] = <model identifier>
  }
```

##### Deploying Base LLM with LoRA Head

Please see the [example](</examples/finetuning_example.ipynb>) to see how to upload the trained LORA head to the Hugging Face Hub.

To deploy a base LLM model with a LORA head, we would need to first download the LORA head from the Hugging Face Hub.

1. Install the `huggingface-cli`

```bash
pip install --upgrade huggingface_hub
```

2. Login to the Hugging Face Hub

```bash
huggingface-cli login
```

3. Download the LORA head

```bash
huggingface-cli download <LORA head path on Huggingface Hug> --local-dir lora_head
```

Then add an entry in the [configs/chat_models.pkl](</configs/chat_models.pkl>) that follows the following format:

```pkl
catMemoExample: ChatModelConfig = new {
  chat_model = "finnlp-challenge-finetuned-llama3-8b-task1"  # the name of LORA head, which should be the same as the "model" name in Hugging Face Hub
  lora = true  # set it as true
  lora_path = "lora_head"  # the path to where the LORA head is saved
  lora_base_model = "meta-llama/Meta-Llama-3-8B-Instruct"  # the base model for the LORA head
  chat_model_type = "instruction"
  chat_model_inference_engine = "vllm"
  chat_endpoint = null
  chat_template_path = null
  chat_system_message = "You are a helpful assistant."
  chat_parameters = new Mapping {}
}
```

Also add the entry in the registry.

```pkl
chat_model_dict = new Mapping {
    ["catMemo"] = catMemoExample
  }
```

#### Meta Config

The meta config contains the configuration for the framework. The configuration is located at [configs/main.pkl](<"/configs/main.pkl">) from line 9 to line 29, which contains the following information:

```pkl
hidden config = new meta.MetaConfig {
    run_name = "exp"  # the run name can be set to any string
    agent_name = "finmem_agent"  # also can be set to any string
    trading_symbols = new Listing {
            "BTC-USD"  # the trading symbol. In our case, it either be "BTC-USD" or "ETH-USD"
    }
    warmup_start_time = "2023-02-11"  # do not change this config
    warmup_end_time = "2023-03-10"  # do not change this config
    test_start_time = "2023-03-11"  # do not change this config
    test_end_time = "2023-04-04"  # do not change this config
    top_k = 5  # do not change this config
    look_back_window_size = 3  # do not change this config
    momentum_window_size = 3  # do not change this config
    tensor_parallel_size = 2  # set the tensor parallel size for VLLM, usually set to the number of gpus available
    embedding_model = "text-embedding-3-large"  # do not change this config
    chat_model = "catMemo"  # the chat model's identifier in the chat model registry
    chat_vllm_endpoint = "http://0.0.0.0:8000"  # set this to the VLLM server endpoint, default to localhost port 8000
    chat_parameters = new Mapping {
        ["temperature"] = 0.6 # do not change this config
    }
}
```

#### Generate Config

1. Build evaluation docker container.

```bash
docker build -t finmem-coling -f Dockerfile .
```

2. Compile and generate the configuration file.

```bash
docker run -it -v .:/workspace --network host finmem-coling config
```

### Deploy Qdrant Vector Database

1. Start a new shell session, the Qdrant server will need to be running in the background.

2. Pull the Qdrant docker image.

```bash
docker pull qdrant/qdrant
```

3. Start the Qdrant server.

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### Deploy VLLM Server

1. Start a new shell session, the VLLM server will need to be running in the background.

2. Pull the VLLM docker image.

```bash
docker pull vllm/vllm-openai:v0.6.2
```

3. Start running the VLLM server.

```bash
bash scripts/start_vllm.sh
```

### Running Framework

After deploying the VLLM server and Qdrant vector database, we can run the evaluation framework to assess trading performance. The system need to first be warmed up before running the evaluation framework.

1. Running warm-up.

```bash
docker run -it -v .:/workspace --network host finmem-coling warmup
```

If the warm-up is interrupted (OpenAI API error, etc.), please use the following command to resume from the last checkpoint.

```bash
docker run -it -v .:/workspace --network host finmem-coling warmup-checkpoint
```

2. Running testing.

```bash
docker run -it -v .:/workspace --network host finmem-coling test
```

The test can also be resumed from the last checkpoint.

```bash
docker run -it -v .:/workspace --network host finmem-coling test-checkpoint
```

3. Generate metric report.

```bash
docker run -it -v .:/workspace --network host finmem-coling eval
```

The results will be saved in the `results/<run_name>/<chat_model>/<trading_symbols>/metrics` directory.
