import tensorflow as tf
import pickle

class get_clothes_class():
    def __init__(self, model_path, tokenizer_path, encoded_word_dict_path):
        self.classes = ["outwear", "top", "trousers", "women dresses", "women skirts"]
        ### Import model
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
            f.close()
        ### Import tokenizer
        with open(tokenizer_path, 'rb') as f:
            self.tokenizer = pickle.load(f)
            f.close()
        ### Import decoding dictionary
        with open(encoded_word_dict_path, 'rb') as f:
            self.word_keys = pickle.load(f)
            f.close()
    
    '''plaintext to encoded words format'''
    def _encode_input(self, raw_string):
        raw_string_list = raw_string.split()
        encoded_string_list = [self.word_keys[i.lower()] for i in raw_string_list if i.lower() in self.word_keys.keys()]
        return ' '.join(encoded_string_list)    
    
    '''to process the encoded words for model prediction'''    
    def process_input(self, input_string):
        # Convert words into encoded input
        encoded_input_string = self._encode_input(input_string)
        print('encoded words: ', encoded_input_string)
        # Tokenise and transform your encoded input
        processed_input=self.tokenizer.transform([encoded_input_string])
        # Pass the processed input into the prediction
        result = self.model.predict(processed_input)
        #Get classes result
        detected_classes = [self.classes[idx] for idx,item in enumerate(result[-1]) if item==1]
        return detected_classes


### Example usage ###
# clothes=get_clothes_class('./fashion/model.pkl','./fashion/cvect.pkl','./fashion/encoded_words.pkl')
# result = clothes.process_input("blouse")
# print(result)