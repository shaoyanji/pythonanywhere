'use strict';

const WASM_URL = '/static/wasm.wasm';
var wasm;

function init() {
    const go = new Go();

    if ('instantiateStreaming' in WebAssembly) {
        WebAssembly.instantiateStreaming(fetch(WASM_URL), go.importObject).then(function (obj) {
            wasm = obj.instance;
            go.run(wasm);
        })
    } else {
        fetch(WASM_URL).then(response =>
            response.arrayBuffer()
        ).then(bytes =>
            WebAssembly.instantiate(bytes, go.importObject).then(function (obj) {
                wasm = obj.instance;
                go.run(wasm);
            })
        );
    }
}

init();
