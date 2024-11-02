package com.PepsiMaxx.Smarthack.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

import java.net.URI;
import java.net.URISyntaxException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

@RestController
@RequestMapping("/api/")
public class PlayController {

    @PostMapping("/session/start")
    public Mono<String> startSession() {
        try {
            HttpClient client = HttpClient.newHttpClient();

            URI uri = new URI("http://localhost:8080/api/v1/session/start");
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(uri)
                    .header("API-KEY", "7bcd6334-bc2e-4cbf-b9d4-61cb9e868869")
                    .POST(HttpRequest.BodyPublishers.noBody())
                    .build();

            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                return Mono.just("Session key: " + response.body());
            } else {
                return Mono.error(new RuntimeException("Failed to start session: " + response.statusCode()));
            }
        } catch (URISyntaxException e) {
            return Mono.error(new RuntimeException("Invalid URI syntax: " + e.getMessage()));
        } catch (Exception e) {
            return Mono.error(new RuntimeException("Error while sending the request: " + e.getMessage()));
        }
    }
}
