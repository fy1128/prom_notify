FROM python:3.6-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN set -eux; \
	\
	runDeps=' \
		libxslt-dev \
	'; \
	apk add --no-cache --virtual .build-deps \
		$runDeps \
		build-base \
		python-dev \
		musl-dev \
		libffi-dev \
		portaudio-dev \
		zlib-dev \
		jpeg-dev \
		libxml2-dev \
	; \
	\
	pip install --no-cache-dir -r requirements.txt; \
	\
	runDeps="$runDeps $( \
		scanelf --needed --nobanner --format '%n#p' --recursive /usr/local \
			| tr ',' '\n' \
			| sort -u \
			| awk 'system("[ -e /usr/local/lib/" $1 " ]") == 0 || /libc.so./ { next } { print "so:" $1 }' \
	)"; \
	apk add --virtual .run-deps $runDeps; \
	apk del .build-deps; 

COPY . .

CMD [ "python", "./pn.py" ]

