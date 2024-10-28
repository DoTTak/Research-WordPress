FROM php:8.3-apache

# Rewrite URLs with mod_rewrite
RUN a2enmod rewrite

# mysqli extension
RUN docker-php-ext-install mysqli