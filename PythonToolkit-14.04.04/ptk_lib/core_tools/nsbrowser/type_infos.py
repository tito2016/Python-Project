"""
Module conatinging callables to get info/value string for NSBrowser

format: callable(eng, oname)
"""

def infovalue(eng,oname):
    """
    Used by the namespace browsers info/value column defaults to string 
    representation of object returned by __repr__
    """
    res = eng.evaluate('str('+oname+')')    
    return res

