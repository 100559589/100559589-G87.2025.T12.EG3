"""MODULE: transfer_request. Contains the transfer request class"""
import hashlib
import json
import re
from datetime import datetime, timezone
from account_management_exception import AccountManagementException

class TransferRequest:
    """Class representing a transfer request"""
    #pylint: disable=too-many-arguments
    def __init__(self,
                 from_iban: str,
                 transfer_type: str,
                 to_iban:str,
                 transfer_concept:str,
                 transfer_date:str,
                 transfer_amount:float,
                 transfer_store_file:str):


        self.__transfer_store_file = transfer_store_file
        self.__from_iban = from_iban
        self.__to_iban = to_iban
        self.__transfer_type = transfer_type
        self.__concept = transfer_concept
        self.__transfer_date = transfer_date
        self.__transfer_amount = transfer_amount
        justnow = datetime.now(timezone.utc)
        self.__time_stamp = datetime.timestamp(justnow)

        self.validate_iban(from_iban)
        self.validate_iban(to_iban)
        self.validate_concept(transfer_concept)
        self.validate_transfer_type(transfer_type)
        self.validate_transfer_date(transfer_date)
        self.validate_amount(transfer_amount)
        self.store_transfer_request()

    def validate_iban(self, iban: str):
        """
    Calcula el dígito de control de un IBAN español.

    Args:
        iban (str): El IBAN sin los dos últimos dígitos (dígito de control).

    Returns:
        str: El dígito de control calculado.

        """
        is_valid_iban = self.check_regular(r"^ES[0-9]{22}", iban)
        if not is_valid_iban:
            raise AccountManagementException("Invalid IBAN format")
        original_code = iban[2:4]
        #replacing the control
        iban = iban[:2] + "00" + iban[4:]
        iban = iban[4:] + iban[:4]


        # Convertir el IBAN en una cadena numérica, reemplazando letras por números
        iban = (iban.replace('A', '10').replace('B', '11').
                replace('C', '12').replace('D', '13').replace('E', '14').
                replace('F', '15'))
        iban = (iban.replace('G', '16').replace('H', '17').
                replace('I', '18').replace('J', '19').replace('K', '20').
                replace('L', '21'))
        iban = (iban.replace('M', '22').replace('N', '23').
                replace('O', '24').replace('P', '25').replace('Q', '26').
                replace('R', '27'))
        iban = (iban.replace('S', '28').replace('T', '29').replace('U', '30').
                replace('V', '31').replace('W', '32').replace('X', '33'))
        iban = iban.replace('Y', '34').replace('Z', '35')

        # Mover los cuatro primeros caracteres al final

        # Convertir la cadena en un número entero
        int_iban = int(iban)

        # Calcular el módulo 97
        mod = int_iban % 97

        # Calcular el dígito de control (97 menos el módulo)
        control_digit = 98 - mod

        if int(original_code) != control_digit:
            #print(control_digit)
            raise AccountManagementException("Invalid IBAN control digit")

        return iban

    def validate_concept(self, concept: str):
        """regular expression for checking the minimum and maximum length as well as
        the allowed characters and spaces restrictions
        there are other ways to check this"""
        is_valid_concept = self.check_regular(r"^(?=^.{10,30}$)([a-zA-Z]+(\s[a-zA-Z]+)+)$", concept)
        if not is_valid_concept:
            raise AccountManagementException ("Invalid concept format")

    @staticmethod
    def check_regular(pattern, value):
        """Check that value is in pattern"""
        my_regex = re.compile(pattern)
        is_in_regex = my_regex.fullmatch(value)
        return is_in_regex

    def validate_transfer_date(self, transfer_date):
        """validates the arrival date format  using regex"""
        valid_transfer_date = self.check_regular(r"^(([0-2]\d|3[0-1])\/(0\d|1[0-2])\/\d\d\d\d)$",
                                                 transfer_date)
        if not valid_transfer_date:
            raise AccountManagementException("Invalid date format")

        try:
            my_date = datetime.strptime(transfer_date, "%d/%m/%Y").date()
        except ValueError as ex:
            raise AccountManagementException("Invalid date format") from ex

        if my_date < datetime.now(timezone.utc).date():
            raise AccountManagementException("Transfer date must be today or later.")

        if my_date.year < 2025 or my_date.year > 2050:
            raise AccountManagementException("Invalid date format")
        return transfer_date
    #pylint: disable=too-many-arguments
    def transfer_request(self)->str:
        """first method: receives transfer info and
        stores it into a file"""



    def validate_amount(self, amount):
        """validates transfer amount"""
        try:
            amount_float = float(amount)
        except ValueError as exc:
            raise AccountManagementException("Invalid transfer amount") from exc
        n_str = str(amount_float)
        if '.' in n_str:
            decimals = len(n_str.split('.')[1])
            if decimals > 2:
                raise AccountManagementException("Invalid transfer amount")
        if amount_float < 10 or amount_float > 10000:
            raise AccountManagementException("Invalid transfer amount")

    def validate_transfer_type(self, transfer_type):
        """checks if transfer type is valid"""
        is_valid_transfer_type = self.check_regular(r"(ORDINARY|INMEDIATE|URGENT)", transfer_type)
        if not is_valid_transfer_type:
            raise AccountManagementException("Invalid transfer type")

    def store_transfer_request(self):
        '''stores transfer request if valid'''
        try:
            with open(self.__transfer_store_file, "r", encoding="utf-8", newline="") as file1:
                t_l = json.load(file1)
        except FileNotFoundError:
            t_l = []
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex
        for t_i in t_l:
            self.is_duplicate_transfer(t_i)
        t_l.append(self.to_json())

        try:
            with open(self.__transfer_store_file, "w", encoding="utf-8", newline="") as file2:
                json.dump(t_l, file2, indent=2)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex



    def is_duplicate_transfer(self, t_i):
        """checks if transfer is a duplicate"""
        if (t_i["from_iban"] == self.from_iban and
                t_i["to_iban"] == self.to_iban and
                t_i["transfer_date"] == self.transfer_date and
                t_i["transfer_amount"] == self.transfer_amount and
                t_i["transfer_concept"] == self.transfer_concept and
                t_i["transfer_type"] == self.transfer_type):
            raise AccountManagementException("Duplicated transfer in transfer list")


    def __str__(self):
        return "Transfer:" + json.dumps(self.__dict__)

    def to_json(self):
        """returns the object information in json format"""
        return {
            "from_iban": self.__from_iban,
            "to_iban": self.__to_iban,
            "transfer_type": self.__transfer_type,
            "transfer_amount": self.__transfer_amount,
            "transfer_concept": self.__concept,
            "transfer_date": self.__transfer_date,
            "time_stamp": self.__time_stamp,
            "transfer_code": self.transfer_code
        }
    @property
    def from_iban(self):
        """Sender's iban"""
        return self.__from_iban

    @from_iban.setter
    def from_iban(self, value):
        self.__from_iban = value

    @property
    def to_iban(self):
        """receiver's iban"""
        return self.__to_iban

    @to_iban.setter
    def to_iban(self, value):
        self.__to_iban = value

    @property
    def transfer_type(self):
        """Property representing the type of transfer: REGULAR, INMEDIATE or URGENT """
        return self.__transfer_type
    @transfer_type.setter
    def transfer_type(self, value):
        self.__transfer_type = value

    @property
    def transfer_amount(self):
        """Property respresenting the transfer amount"""
        return self.__transfer_amount
    @transfer_amount.setter
    def transfer_amount(self, value):
        self.__transfer_amount = value

    @property
    def transfer_concept(self):
        """Property representing the transfer concept"""
        return self.__concept
    @transfer_concept.setter
    def transfer_concept(self, value):
        self.__concept = value

    @property
    def transfer_date( self ):
        """Property representing the transfer's date"""
        return self.__transfer_date
    @transfer_date.setter
    def transfer_date( self, value ):
        self.__transfer_date = value

    @property
    def time_stamp(self):
        """Read-only property that returns the timestamp of the request"""
        return self.__time_stamp

    @property
    def transfer_code(self):
        """Returns the md5 signature (transfer code)"""
        return hashlib.md5(str(self).encode()).hexdigest()
