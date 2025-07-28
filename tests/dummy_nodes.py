from src.core.node_interface import asda_node, BaseInputSchema, BaseOutputSchema

class LLMInput(BaseInputSchema):
    prompt: str

class LLMOutput(BaseOutputSchema):
    response: str

@asda_node(name="llm_inference_node", version="1.0")
def llm_inference_node(data: LLMInput) -> LLMOutput:
    return LLMOutput(response=f"Response to: {data.prompt}")

class RetrieverInput(BaseInputSchema):
    query: str

class RetrieverOutput(BaseOutputSchema):
    documents: list[str]

@asda_node(name="retriever_node", version="1.0")
def retriever_node(data: RetrieverInput) -> RetrieverOutput:
    return RetrieverOutput(documents=[f"Document for: {data.query}"])

class ExecutorInput(BaseInputSchema):
    action: str

class ExecutorOutput(BaseOutputSchema):
    result: str

@asda_node(name="executor_node", version="1.0")
def executor_node(data: ExecutorInput) -> ExecutorOutput:
    return ExecutorOutput(result=f"Executed: {data.action}")
