import neo4j_utils as nu
import yaml
import sys
import os
from biochatter.prompts import BioCypherPromptEngine
from biochatter.llm_connect import AzureGptConversation

from dotenv import load_dotenv
import json

def jaccard_similarity(list1, list2):
    s1 = set(list1)
    s2 = set(list2)
    return float(len(s1.intersection(s2)) / len(s1.union(s2)))


URI = "bolt://localhost:7687"
DB_NAME = None
AUTH = None
SCHEMA_FILE = "C:/Pistoia/BioCypher-OT/config/schema_config.yaml"

# DEPLOYMENT_NAME = 'gpt-4-turbo'
# MODEL_NAME = 'gpt-4-turbo'
DEPLOYMENT_NAME = 'gpt-35-turbo'
MODEL_NAME = 'gpt-35-turbo'
VERSION = '2023-12-01-preview'

neodriver = nu.Driver(
        db_name=DB_NAME or "neo4j",
        db_uri=URI,
    )
question = "what HumanGenes are related to Disease cancer?"
gold_query = 'MATCH (g:HumanGene)-[:GeneToDiseaseAssociation]-(d:Disease {name: "cancer"}) RETURN  g'
# how explicit should the questions be? humans implicitly have expectations they never explicitly say.

gold_result = neodriver.query(gold_query)[0]
print(len(gold_result))

gold_elements = {}
for e in gold_result:
    for k, v in e.items():
        if isinstance(v, dict):
            for k1, v1 in v.items():
                gold_elements[k1] = gold_elements.get(k1, set()) | {v1}
        else:
            gold_elements[k] = gold_elements.get(k, set()) | {v}

with open(SCHEMA_FILE) as file:
    schema_dict = yaml.safe_load(file)
    
def conversation_factory():
    conversation = AzureGptConversation(
        model_name=MODEL_NAME, 
        deployment_name=DEPLOYMENT_NAME,
        version=VERSION,
        prompts={},
        correct=False,
    )
    conversation.set_api_key(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"), user="test_user"
    )
    return conversation

# prompt_engine = AzureBioCypherPromptEngine(
#     schema_config_or_info_dict=schema_dict,
#     model_name=MODEL_NAME,
#     deployment_name=DEPLOYMENT_NAME
#                                       )

prompt_engine = BioCypherPromptEngine(
    schema_config_or_info_dict=schema_dict,
    model_name=MODEL_NAME,
    conversation_factory=conversation_factory
                                      )

query = prompt_engine.generate_query(question, 'Neo4j')

llm_result = neodriver.query(query)[0]


if not llm_result:
    print('invalid query or no entities found')
else:
    llm_elements = {}

    for e in llm_result:
        if isinstance(e, dict):
            for k, v in e.items():
                if isinstance(v, dict):
                    for k1, v1 in v.items():
                        llm_elements[k1] = llm_elements.get(k1, set()) | {v1}
                else:
                    llm_elements[k] = llm_elements.get(k, set()) | {v}

    for k, v in llm_elements.items():
        print(k)
        max_score = 0
        for k1, v1 in gold_elements.items():
            score = jaccard_similarity(v, v1)
            if score > max_score:
                max_score = score
        print(max_score)