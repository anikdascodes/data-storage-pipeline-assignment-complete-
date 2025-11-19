FROM apache/spark-py:v3.5.0

# Switch to root to install packages
USER root

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Set working directory
WORKDIR /workspace

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

# Set environment variables (Spark already configured in base image)
ENV PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH

CMD ["/bin/bash"]
