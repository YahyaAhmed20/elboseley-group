(function () {
    qz.security.setCertificatePromise(function (resolve, reject) {
        fetch("/static/qz/digital-certificate.txt", {
            cache: "no-store",
            headers: {
                "Content-Type": "text/plain"
            }
        })
        .then(function (response) {
            if (response.ok) {
                return response.text();
            }
            throw new Error("Failed to load QZ certificate");
        })
        .then(resolve)
        .catch(reject);
    });

    qz.security.setSignatureAlgorithm("SHA512");

    qz.security.setSignaturePromise(function (toSign) {
        return function (resolve, reject) {
            fetch(
                "/service/qz/sign/?request=" + encodeURIComponent(toSign),
                {
                    cache: "no-store",
                    headers: {
                        "Content-Type": "text/plain"
                    }
                }
            )
            .then(function (response) {
                if (response.ok) {
                    return response.text();
                }
                throw new Error("Failed to sign QZ request");
            })
            .then(resolve)
            .catch(reject);
        };
    });
})();