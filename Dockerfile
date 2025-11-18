FROM apache/spark:3.5.0

# Switch to root user to install packages
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    procps \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Spark is already installed in the base image
# Set Spark environment variables (already set in base image but ensuring consistency)
ENV SPARK_HOME=/opt/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH

# Set working directory
WORKDIR /workspace

# Copy requirements and install Python packages
# PySpark is already installed in the base image, install only additional packages
COPY requirements.txt .
RUN pip3 install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org pyyaml==6.0.1 pandas==2.0.3

# Download Hudi and Hadoop dependencies to avoid runtime downloads
# Create jars directory
RUN mkdir -p ${SPARK_HOME}/jars

# Download Hudi bundle
RUN wget --no-check-certificate -O ${SPARK_HOME}/jars/hudi-spark3.5-bundle_2.12-0.15.0.jar \
    https://repo1.maven.org/maven2/org/apache/hudi/hudi-spark3.5-bundle_2.12/0.15.0/hudi-spark3.5-bundle_2.12-0.15.0.jar || \
    echo "Warning: Could not download Hudi bundle"

# Download Hadoop AWS
RUN wget --no-check-certificate -O ${SPARK_HOME}/jars/hadoop-aws-3.3.4.jar \
    https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar || \
    echo "Warning: Could not download Hadoop AWS"

# Download AWS SDK bundle
RUN wget --no-check-certificate -O ${SPARK_HOME}/jars/aws-java-sdk-bundle-1.12.262.jar \
    https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar || \
    echo "Warning: Could not download AWS SDK bundle"

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
