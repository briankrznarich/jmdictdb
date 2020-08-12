# This module defines the database update id's required by this
# version of the JMdictDB API.  DBVERS is a list of integers,
# conventionally expressed in hexdecimal.  When jdb.dbOpen()
# opens a database connection it will check that each update
# number in DBVERS is present and marked active in database 
# table "db" in the database connected to.  If not, a KeyError
# exception will be raised by jdb.dbOpen().  This is a check
# that the database to be used is at the update level that 
# this JMdictDB API version expects.

DBVERS = [0x329fa4]
