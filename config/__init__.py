# PyMySQL es un conector de MySQL escrito 100 % en Python (no requiere compilar
# nada en Windows). Con esta línea Django lo usa como si fuera "mysqlclient".
import pymysql

pymysql.install_as_MySQLdb()
