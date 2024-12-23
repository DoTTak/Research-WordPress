FROM php:8.3-apache

# Rewrite URLs with mod_rewrite
RUN a2enmod rewrite

# 아파치 설정 변경
RUN sed -i 's/80/8080/g' /etc/apache2/ports.conf && \
    sed -i 's/:80/:8080/g' /etc/apache2/sites-enabled/000-default.conf

# 아파치 포트 노출
EXPOSE 8080

# mysqli extension
RUN docker-php-ext-install mysqli