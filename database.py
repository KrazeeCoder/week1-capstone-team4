import pickle

# contains fingerprints & song info
# each fingerprint is a list of tuples

class AudioDatabase:
      def __init__(self):
            self.data = {}
      
      def __init__(self, data):
            self.data = data

      def save_data(self):
            with open("data.pkl", mode="wb") as opened_file:
                  pickle.dump(self.data, opened_file)
      
      def load_data(self):
            with open("data.pkl", mode="rb") as opened_file:
                  self.data = pickle.load(opened_file)

      
      






      
