from pydantic import BaseModel
from app.models import CompanyDataReturnModel
#i mport gemini-library as per sdk

class Gemini(BaseModel):
    #def init()
    # create messages (system prompt, user prompt)
    
    def request(self, pdf_string):
        # make the request with the self.messages & CompanyDataReturnModel
        
        return response