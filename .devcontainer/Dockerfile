FROM mcr.microsoft.com/devcontainers/python:3.11

ENV PYTHONUNBUFFERED=1 \
	PYTHONDONTWRITEBYTECODE=1 \
	MPLBACKEND=Agg

WORKDIR /workspaces/sports-prediction

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		build-essential \
		libgl1 \
		libglib2.0-0 \
		libjpeg62-turbo \
		libpng-dev \
		libfreetype6 \
		curl \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt requirements_phase2.txt requirements_phase2_fixed.txt requirements_phase2_no_tf.txt ./

RUN pip install --upgrade pip \
	&& pip install -r requirements.txt \
	&& pip install -r requirements-dev.txt \
	&& pip install -r requirements_phase2.txt \
	&& pip install -r requirements_phase2_fixed.txt \
	&& pip install -r requirements_phase2_no_tf.txt

CMD ["sleep", "infinity"]
