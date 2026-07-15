# Step 1: Use a lightweight Python base image
FROM python:3.11-slim

# Step 2: Establish the folder where our app will run inside the container
WORKDIR /app

# Step 3: Copy only the requirements file first to optimize cache speeds
COPY app/requirements.txt .

# Step 4: Install the external libraries cleanly
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the application source code into the working directory
COPY app/ .

# Step 6: Inform Docker we communicate on Port 5000
EXPOSE 5000

# Step 7: Launch Gunicorn from within the active /app directory
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]