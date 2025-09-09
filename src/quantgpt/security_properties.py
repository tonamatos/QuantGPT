from pydantic import BaseModel
from typing import List, Optional 

class Reference(BaseModel):
    topic: str
    reference: str

# Allowing for the storing of context for each security component
class ItemWithContext(BaseModel):
    name: str              
    context: Optional[str] 

# Creates a class for the outputs
class SecurityPropertiesModel(BaseModel):
    encryption_algorithms: List[ItemWithContext]        
    protocols: List[ItemWithContext]                     
    certificates: List[ItemWithContext]                 
    key_lifetimes: List[ItemWithContext]               
    key_distribution: List[ItemWithContext]          
    authorization: List[ItemWithContext]              
    further_references: List[Reference]

