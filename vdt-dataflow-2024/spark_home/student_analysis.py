from pyspark.sql import *

from pyspark.sql.functions import *
from pyspark.sql.types import *

spark = SparkSession.builder \
    .appName("Student Activity Analysis") \
    .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
    .getOrCreate()

schema = StructType([
    StructField("student_code", IntegerType(), True),
    StructField("student_name", StringType(), True)
])

student_info_path = "hdfs://namenode:9000/raw_zone/fact/student_info"
student_info_df = (spark.read.option("encoding", "UTF-8")
                   .option("compression", "snappy")
                   .csv(student_info_path, schema=schema))

log_action_path = "hdfs://namenode:9000/raw_zone/fact/activity"
log_action_df = (spark.read.option("header", "true")
                 .option("compression", "snappy")
                 .parquet(log_action_path))

# check
# log_action_df.show(5)
# student_info_df.show(5)
# log_action_df.printSchema()
# student_info_df.printSchema()

joined_df = log_action_df.join(student_info_df, "student_code")

result_df = joined_df.groupBy("student_code", "student_name", "activity", "timestamp") \
    .agg(count("numberOfFile").alias("totalFile")) \
    .withColumn("date", date_format(to_date(col("timestamp"), "MM/dd/yyyy"), "yyyyMMdd")) \
    .select("date", "student_code", "student_name", "activity", "totalFile") \
    .orderBy("date")

# result_df.printSchema()
# result_df.show()

students = result_df.select("student_name").distinct().collect()

output_dir = "/home/output"

for student in students:
    student_name = student['student_name']
    student_data = result_df.filter(result_df.student_name == student_name)

    file_name = f"{output_dir}/{student_name.replace(' ', '_')}.csv"

    student_data.coalesce(1).write.csv(file_name, mode="overwrite", header=False)

spark.stop()
