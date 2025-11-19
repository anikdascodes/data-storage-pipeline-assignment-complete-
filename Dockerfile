FROM eclipse-temurin:11-jdk-jammy

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    wget \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Spark
ENV SPARK_VERSION=3.5.0
ENV HADOOP_VERSION=3
ENV SPARK_HOME=/opt/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH

# Download Spark from CDN mirror (faster than Apache archives)
RUN wget -q --timeout=300 --tries=3 \
    https://dlcdn.apache.org/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz || \
    wget -q --timeout=300 --tries=3 \
    https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    tar -xzf spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    mv spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} ${SPARK_HOME} && \
    rm spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz

# Set working directory
WORKDIR /workspace

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Create data directories
RUN mkdir -p /workspace/data/raw/seller_catalog && \
    mkdir -p /workspace/data/raw/company_sales && \
    mkdir -p /workspace/data/raw/competitor_sales && \
    mkdir -p /workspace/data/processed && \
    mkdir -p /workspace/data/quarantine

# Copy project files
COPY configs /workspace/configs
COPY src /workspace/src
COPY scripts /workspace/scripts

# Make scripts executable
RUN chmod +x /workspace/scripts/*.sh

CMD ["/bin/bash"]
