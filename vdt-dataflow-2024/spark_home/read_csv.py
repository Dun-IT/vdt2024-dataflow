from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("Read CSV") \
    .getOrCreate()

file_path = "/home/output/Nguyễn_Khoa_Đoàn.csv"

df = spark.read.option("encoding", "utf-8").csv(file_path, header=False)

df.show()

spark.stop()
