import re
from difflib import SequenceMatcher
from typing import final
from fuzzywuzzy import fuzz

class VehicleModelMatcher:
    def __init__(self,database_names):
        self.database_names= database_names
        self.brand_model_map=self._create_brand_model_map()

    # create a map of brand to models
    def _create_brand_model_map(self):
        brand_model_map={}
        for db_name in self.database_names:
            brand, model=db_name.split('_',1)
            if brand not in brand_model_map:
                brand_model_map[brand]=[]
            brand_model_map[brand].append(model)
        return brand_model_map

    def preprocess_input(self, input_string):
        # remove special charcters and convert to lowercase
        return re.sub(r'[^a-zA-Z0-9 ]', '', input_string.lower())
    
    # for extracting brand and model from the input string
    def extract_brand_and_model(self, input_string):
        words=input_string.split()
        for i in range(len(words)):
            # check if the word is a brand
            potential_brand=' '.join(words[:i+1])
            if potential_brand in self.brand_model_map:
                return potential_brand, ' '.join(words[i+1:])
            return None, input_string


    def get_best_match(self, input_string):
        preprocessed_input=self.preprocess_input(input_string)
        extracted_brand, extracted_model=self.extract_brand_and_model(preprocessed_input)
        best_match=None
        best_score=0

        if extracted_brand:
            for model in self.brand_model_map[extracted_brand]:
                db_name=f"{extracted_brand}_{model}"
                score=self.calculate_match_score(preprocessed_input, db_name)

                if score>best_score:
                    best_score=score
                    best_match=db_name
        else:
            for db_name in self.database_names:
                # split the databse name into brand and model
                brand,model=db_name.split('_',1)

                # check if the brand is present or not
                if brand in preprocessed_input:
                # claculate the similarity retio
                    ratio=SequenceMatcher(None, preprocessed_input, db_name.replace('_',' ')).ratio()
                    if ratio>best_ratio:
                        best_ratio=ratio
                        best_match=db_name

        return best_match, best_score
    
    def calculate_match_score(self, input_string, db_name,extracted_model=None):
        db_brand, db_model=db_name.split('_',1)
        # brand match
        brand_score=fuzz.ratio(db_brand, input_string.split()[0])/100

        # model match
        if extracted_model:
            model_score=fuzz.partial_ratio(db_model, extracted_model)/100
        else:
            model_score=fuzz.partial_ratio(db_model, input_string)/100

        seq_score=SequenceMatcher(None, input_string, db_name.replace('_',' ')).ratio()

        final_score=(brand_score *0.3 +model_score * 0.5 + seq_score * 0.2) *100

        return final_score

# Database names
database_names = [
    "ford_aspire", "ford_ecosport", "ford_endeavour", "ford_figo",
    "honda_amaze", "honda_city", "honda_wr_v",
    "hyundai_aura", "hyundai_grand_i10", "hyundai_i10",
    "hyundai_i20", "hyundai_venue", "hyundai_verna",
    "mahindra_bolero", "mahindra_marazzo", "mahindra_thar",
    "mahindra_tuv300", "mahindra_xuv300", "mahindra_xuv500",
    "maruti_ertiga", "maruti_swift", "maruti_vitara_brezza",
    "maruti_wagonr", "maruti_baleno", "maruti_ciaz",
    "tata_altroz", "tata_harrier", "tata_nexon",
    "tata_tiago", "tata_tigor", "tata_safari",
    "toyota_fortuner", "toyota_glanza", "toyota_innova_crysta",
    "toyota_yaris"
]

matcher=VehicleModelMatcher(database_names)

test_cases = [
    "FORD INDIA PVT LTD-FIGOASPIRE 1.2 PETROL TREND+MT",
    "FORD INDIA PVT LTD-FORD FIGO ASPIRE 1.5 TDCI DIES",
    "FORD INDIA PVT LTD-FIGOASPIRE 1.5 PETROL TITNMAT",
    "FORD INDIA PVT LTD-FIGO 1.5 D AMBIENT MT BS IV",
    "HYUNDAI MOTOR INDIA LTD-AURA 1.2MT KAPPA SX",
    "HYUNDAI MOTOR INDIA LTD-AURA 1.2MT KAPPA SX(O)",
    "NA-AURA 1.2MT CRDI S",
    "HYUNDAI MOTOR INDIA LTD-AURA 1.2AMT KAPPA SX+"
]

# run test cases
for case in test_cases:
    best_match, confidence = matcher.get_best_match(case)

    print(f"Input: {case}")
    print(f"Best Match: {best_match}")
    print(f"Confidence: {confidence}")
    print("\n")