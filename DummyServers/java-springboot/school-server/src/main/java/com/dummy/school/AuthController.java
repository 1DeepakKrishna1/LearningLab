package com.dummy.school;

import io.swagger.v3.oas.annotations.security.SecurityRequirements;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

/** Username/password -> JWT. This endpoint is public (no auth required). */
@RestController
@RequestMapping("/auth")
@Tag(name = "Auth")
@SecurityRequirements   // overrides the global security requirement -> this endpoint is open
class AuthController {

    private final JwtService jwt;
    private final String user;
    private final String pass;

    AuthController(JwtService jwt,
                   @Value("${auth.user:admin}") String user,
                   @Value("${auth.pass:password}") String pass) {
        this.jwt = jwt;
        this.user = user;
        this.pass = pass;
    }

    @PostMapping("/login")
    public Map<String, Object> login(@RequestBody LoginRequest req) {
        if (!user.equals(req.username()) || !pass.equals(req.password())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid username or password");
        }
        return Map.of(
                "access_token", jwt.createToken(req.username()),
                "token_type", "bearer",
                "expires_in", jwt.getExpSeconds()
        );
    }

    record LoginRequest(String username, String password) {}
}
