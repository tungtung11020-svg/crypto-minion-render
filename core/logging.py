import logging, re, sys
class Redact(logging.Filter):
    pattern=re.compile(r'KM-(?:[A-Z2-7]{4}-){7}[A-Z2-7]{4}',re.I)
    def filter(self,record):
        record.msg=self.pattern.sub('KM-[СКРЫТО]',record.getMessage()); record.args=()
        return True
def configure_logging():
    h=logging.StreamHandler(sys.stdout); h.addFilter(Redact()); h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
    logging.basicConfig(level=logging.INFO,handlers=[h],force=True)
