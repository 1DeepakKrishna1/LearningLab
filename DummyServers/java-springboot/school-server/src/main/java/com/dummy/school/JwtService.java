package com.dummy.school;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/** Issues and validates HS256 JWTs. */
@Service
public class JwtService {

    private final SecretKey key;
    private final long expSeconds;

    public JwtService(
            @Value("${auth.jwt-secret:my-super-secret-jwt-key-change-me-please-32+chars}") String secret,
            @Value("${auth.jwt-exp-seconds:3600}") long expSeconds) {
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.expSeconds = expSeconds;
    }

    public long getExpSeconds() {
        return expSeconds;
    }

    public String createToken(String username) {
        Date now = new Date();
        Date exp = new Date(now.getTime() + expSeconds * 1000);
        return Jwts.builder()
                .subject(username)
                .issuedAt(now)
                .expiration(exp)
                .signWith(key)
                .compact();
    }

    /** Returns the subject if the token is valid, otherwise throws. */
    public String validateAndGetSubject(String token) {
        Claims claims = Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
        return claims.getSubject();
    }
}
