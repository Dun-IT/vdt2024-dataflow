# Báo cáo - VDT2024 DE

#### Sinh viên: Nguyễn Khoa Đoàn

## 1. Mô tả cách triển khai nền tảng
Kiến trúc:
![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/overview.png?raw=true)

Container hoá toàn bộ nền tảng vào trong docker, bao gồm:

##### Kafka chạy trên Zookeeper

- Zookeeper: confluentinc/cp-zookeeper:7.1.0, port 2181:2181, biến config:

```yml
ZOOKEEPER_CLIENT_PORT: 2181
ZOOKEEPER_TICK_TIME: 2000
ZOOKEEPER_INIT_LIMIT: 5
ZOOKEEPER_SYNC_LIMIT: 2
```

- Kafka (broker01): confluentinc/cp-kafka:7.1.0, port 9092:9092, biến config:

```yml
KAFKA_BROKER_ID: 1
KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
KAFKA_LISTENERS: PLAINTEXT_HOST://broker01:9092,PLAINTEXT://broker01:9093
KAFKA_ADVERTISED_LISTENERS:PLAINTEXT_HOST://localhost:9092,PLAINTEXT://broker01:9093
KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
KAFKA_JMX_PORT: 9090
KAFKA_LOG_DIRS: /var/log/kafka
KAFKA_NUM_PARTITIONS: 2
KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 100
CONFLUENT_METRICS_ENABLE: 'false'
```

- Giao diện (kafka-ui): provectuslabs/kafka-ui:latest, port 8080, biến config:

```yml
KAFKA_CLUSTERS_0_NAME: vdt-kafka
KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: broker01:9093
KAFKA_CLUSTERS_0_METRICS_PORT: 9090
```

##### Nifi

- image: apache/nifi:latest, port: 8443:8443, biến config:

```yml
NIFI_WEB_HTTP_PORT: 8443
```

##### HDFS

- HDFS bao gồm namenode và datanode

- namenode: bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8, port 9870:9870

- datanode: bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8

- Config: 

```yml
CORE_CONF_fs_defaultFS=hdfs://namenode:9000
CORE_CONF_hadoop_http_staticuser_user=root
CORE_CONF_hadoop_proxyuser_hue_hosts=*
CORE_CONF_hadoop_proxyuser_hue_groups=*
CORE_CONF_io_compression_codecs=org.apache.hadoop.io.compress.SnappyCodec

HDFS_CONF_dfs_webhdfs_enabled=true
HDFS_CONF_dfs_permissions_enabled=false
HDFS_CONF_dfs_namenode_datanode_registration_ip___hostname___check=false
```

##### Spark

- Spark bao gồm master và 1 worker

- spark-master: bde2020/spark-master:latest, port 8081:8080

```yml
INIT_DAEMON_STEP=setup_spark
SPARK_MODE=master
```

- spark-worker: bde2020/spark-worker:latest, port 8082:8081, depend_on: spark-master, gồm 2 core, 2 memory

```yml
INIT_DAEMON_STEP=setup_spark
SPARK_MODE=worker
SPARK_MASTER=spark://spark-master:7077
SPARK_WORKER_CORES=2
SPARK_WORKER_MEMORY=2g
```

- Gõ docker-compose up -d, kiểm tra kết quả trên docker:

![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/docker-compose%20up.png?raw=true)

## 2. Xây dựng chương trình

### 2.1. Viết chương trình đẩy dữ liệu lên Kafka Topic, đọc dữ liệu từng dòng từ file "log_action.csv", đẩy dữ liệu lên topic "vdt2024" mỗi giây

- Tru cập http://localhost:8080/ để vào Kafka UI:

![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/kafka-broker-localhost.png?raw=true)

- Tạo file producer.py. Import các package cần thiết:

```python
import csv
import time
import json
from kafka import KafkaProducer
from kafka.errors import KafkaError
```

- Cấu hình địa chỉ Kafka broker, kafka_topic, đường dẫn thư mục dữ liệu input:

```python
BOOTSTRAP_SERVERS = 'localhost:9092'
TOPIC_NAME = 'vdt2024'
FILE_PATH = 'data/log_action.csv'
```

- Tạo một kafka producer, cấu hình với boostrap_servers và thiết lập value_serializer để chuyển dữ liệu thành JSON và encode utf-8:

```python
producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
```

- Sử dụng try-catch-finally để đọc từng bản ghi trong file, và gửi lên topic vdt2024

```python
    try:
        with open(file_path, mode='r') as file:
            csv_reader = csv.DictReader(file, 
                            fieldnames=['student_code', 'activity', 'numberOfFile', 'timestamp'])
            for row in csv_reader:
                message = {
                    'student_code': int(row['student_code']),
                    'activity': row['activity'],
                    'numberOfFile': int(row['numberOfFile']),
                    'timestamp': row['timestamp']
                }
                producer.send(TOPIC_NAME, message)
                try:
                    print(
                        f"Thành công: {message}")
                except KafkaError as e:
                    print(f"Thất bại: {e}")

                time.sleep(1)
```

-    Mở file chế độ read

-    Ánh xạ các bản ghi trong csv với các trường trong fieldnames

-    Duyệt từng dòng trong csv, tạo message, chuyển student_code và numberOfFile sang dạng số nguyên, gửi message lên Kafka topic, dừng 1 giây để gửi không quá nhanh

```python
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        producer.close()
```

-    Bắt bất kỳ ngoại lệ nào trong quá trình đọc và gửi dữ liệu, finally để đảm bảo producer luôn được đóng lại dù lỗi hay không

- Kiểm tra dữ liệu trên Kafka, topic "vdt2024"

![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/kafka-message-kafka.png?raw=true)

### 2.2. Sử dụng nifi, kéo dữ liệu từ kafka topic "vdt2024", xử lý và lưu trữ dữ liệu xuống HDFS vào đường dẫn "/raw_zone/fact/activity". Dữ liệu dưới dạng parquet

- Truy cập http://localhost:8443/ để vào Nifi:

![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/nifi-ui.png?raw=true)

- Để đọc từ Kafka, ta cần tạo consumer, kéo thả processor ConsumeKafka_2_0, và config:

![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/nifi-kafkaconsumer.png?raw=true)

- Sử dụng processor ConvertRecord để chuyển đổi bản ghi JSON thành Parquet, trỏ ConsumeKafka_2_0 tới processor này:

![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/nifi-convertrecord.png?raw=true)

- Cuối cùng, sử dụng processor PutHDFS để ghi dữ liệu vào HDFS (lưu ý bỏ file config /opt/nifi/nifi-current/core-site.xml,/opt/nifi/nifi-current/hdfs-site.xml vào nifi), và link vào processor ConvertRecord:

![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/nifi-putHDFS.png?raw=true)

- Start:

![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/step3-nifi.png?raw=true)

- Kiểm tra dữ liệu đã được đẩy lên HDFS hay chưa tại [Browsing HDFS](http://localhost:9870/explorer.html#/raw_zone/fact/activity):

![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/nifi2hdfs.png?raw=true)

### 2.3. Lưu trữ file "danh_sach_sv_de.csv" xuống HDFS

- Kéo file "danh_sach_sv_de.csv" lên HDFS ở trong thư mục data vào thư mục "vdt-dataflow-2024/hadoop_home"" đã được mount "./hadoop_home:/home" của HDFS

- Mở terminal, exec vào container namenode, cd home kiểm tra thư mục tồn tại hay chưa:

```bash
docker exec -it vdt-namenode bash
ls
cd home
```

- Tạo thư mục "/raw_zone/fact/student_info" và đẩy lên HDFS bằng câu lệnh:

```bash
hdfs dfs -mkdir -p /raw_zone/fact/student_info
hdfs dfs -put danh_sach_sv_de_csv /raw_zone/fact/student_info
```

- Kiểm tra kết quả tại [Browsing HDFS](http://localhost:9870/explorer.html#/raw_zone/fact/student_info)

![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/putdssvde2HDFS.png?raw=true)

### 2.4. Chương trình xử lý dữ liệu lưu trữ dưới HDFS, sử dụng Apache Spark

Các python code được viết trong spark_home đã được mount với spark (./spark_home:/home) để không phải copy từ local vào container spark. File student_analysis.py dùng để processing dữ liệu

- Tạo SparkSession, và thiết lập spark.sql.legacy.timeParserPolicy thành LEGACY để xử lý chuỗi ngày tháng theo các phiên bản Spark cũ:

```python
spark = SparkSession.builder \
    .appName("Student Activity Analysis") \
    .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
    .getOrCreate()
```

- Định nghĩa schema cho file "danh_sach_sv_de.csv":

```python
schema = StructType([
    StructField("student_code", IntegerType(), True),
    StructField("student_name", StringType(), True)
])
```

- Khai báo đường dẫn, read.csv để đọc file csv, read.parquet để đọc parquet, option để có header, do có tiếng Việt nên cần encoding UTF-8, và do CORE_CONF_io_compression_codecs=org.apache.hadoop.io.compress.SnappyCodec nên cần option("compression","snappy"). student_info được đọc từ file csv, log_action_path đọc từ file parquet.

```python
student_info_path = "hdfs://namenode:9000/raw_zone/fact/student_info"
student_info_df = (spark.read.option("encoding", "UTF-8")
                   .option("compression", "snappy")
                   .csv(student_info_path, schema=schema))

log_action_path = "hdfs://namenode:9000/raw_zone/fact/activity"
log_action_df = (spark.read.option("header", "true")
                 .option("compression", "snappy")
                 .parquet(log_action_path))
```

- Tiến hành join 2 DataFrame lại với nhau dựa trên cột student_code:

```python
joined_df = log_action_df.join(student_info_df, "student_code")
```

- Nhóm các bản ghi theo tên, id, activity và timestamp. Sau đó đếm số lượng file mỗi nhóm, sau đó chuyển định dạng date từ MM/dd/yyyy thành yyyyMMdd tương ứng với yêu cầu đề bài. Cuối cùng sắp xếp lại dữ liệu theo cột date

```python
result_df = joined_df.groupBy("student_code", "student_name", "activity", "timestamp") \
    .agg(count("numberOfFile").alias("totalFile")) \
    .withColumn("date", date_format(to_date(col("timestamp"), "MM/dd/yyyy"), "yyyyMMdd")) \
    .select("date", "student_code", "student_name", "activity", "totalFile") \
    .orderBy("date")
```

- Lấy danh sách các sinh viên, và ghi dữ liệu ra file CSV (Tên các sinh viên không trùng nhau), kết quả được lưu ở thư mục /home/output. 
  
  - .distinct().collect(): loại bỏ giá trị trùng chỉ giữ lại tên sinh viên duy nhất và thu thập các hàng kết quả thành 1 đối tượng row
  
  - Lặp qua từng sinh viên
  
  - student_data.coalesce(1).write.csv(file_name, mode="overwrite", header=False): coalesce đảm bảo 1 tệp được tạo, ghi ở dạng csv, ghi vào tệp nào cùng tên nếu tồn tại.
  
  - Cuối cùng dừng SparkSession

```python
students = result_df.select("student_name").distinct().collect()

output_dir = "/home/output"

for student in students:
    student_name = student['student_name']
    student_data = result_df.filter(result_df.student_name == student_name)

    file_name = f"{output_dir}/{student_name.replace(' ', '_')}.csv"

    student_data.coalesce(1).write.csv(file_name, mode="overwrite", header=False)

spark.stop()
```

- Vào spark master trong container, cd home, và submit job lên spark:

```bash
docker exec -it spark-master /bin/bash
cd home
/spark/bin/spark-submit student_analysis.py
```

- Có thể sử dụng read_csv.py để đọc dữ liệu (viết thêm) hoặc đọc trực tiếp tại thư mục "vdt-dataflow-2024/spark_home/output":

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("Read CSV") \
    .getOrCreate()

file_path = "/home/output/Nguyễn_Khoa_Đoàn.csv"

df = spark.read.option("encoding", "utf-8").csv(file_path, header=False)

df.show()

spark.stop()
```

- Kết quả:

![](https://github.com/Dun-IT/vdt2024-dataflow/blob/main/vdt-dataflow-2024/assets/final-result.png?raw=true)


