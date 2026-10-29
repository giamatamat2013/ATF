# Runs an ATF window program in the browser, on any host that takes a Docker image
# (Render, Fly.io, Railway, Cloud Run, a VPS...). ATF makes Windows programs, so they run through Wine.
#
#   docker build -t atf-web .
#   docker run -p 8080:8080 atf-web                          # runs the website in app/
#   docker run -p 8080:8080 -e ATF_APP=examples/ui/todo.atf atf-web
#   docker run -p 8080:8080 -v "$PWD/myapp:/app" -e ATF_APP=/app/main.atf atf-web
#
# Then open http://localhost:8080/. The host's PORT variable is used when it is set.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    WINEPREFIX=/root/.wine \
    WINEDEBUG=-all \
    WINEARCH=win64

RUN dpkg --add-architecture i386 \
 && apt-get update \
 && apt-get install -y --no-install-recommends wine wine64 xvfb xauth ca-certificates fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /atf
COPY bin/atf.exe bin/atf.exe
COPY stdlib stdlib
COPY atf/stdlib atf/stdlib
COPY examples examples
COPY app app
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# app/main.atf is the starter website (routes in app/site.atf, files in app/public/). Set ATF_APP to run
# another program, for example a window program (examples/ui/counter.atf) that is served as a page.
ENV ATF_APP=app/main.atf \
    PORT=8080
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
