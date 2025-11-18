FROM apache/spark:3.5.0

# Switch to root user to install packages
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    procps \
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
