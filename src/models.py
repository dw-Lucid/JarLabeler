CLASSIFICATIONS = ["Sativa", "Sativa Hybrid", "Hybrid", "Indica Hybrid", "Indica"]

class Strain:
    def __init__(self, name, classification, thc_percent, lineage=''):
        self.name = name
        self.classification = classification
        self.thc_percent = thc_percent
        self.lineage = lineage