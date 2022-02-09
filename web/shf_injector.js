var shf_StyleInjector = {
    inject: (path, mid) => {
        /* Temporary fix for Anki 2.1.50 compatibility 
           until add-on porting guide is published */
        noteEditorPromise.then(() => setTimeout(() => shf_StyleInjector.insertStyles(path, mid)))
    },

    insertStyles: (path, mid) => {
        document.documentElement.setAttribute("mid", mid)
        for (let field of document.getElementsByClassName("editor-field")) {
            const root = field.querySelector(".rich-text-editable").shadowRoot
            const editable = root.querySelector("anki-editable")
            
            editable.setAttribute("mid", mid)

            if (!field.hasAttribute("has-css-injected")) {
                editable.classList.add(...document.body.classList)

                const link = document.createElement("link")
                link.href = path
                link.type = "text/css"
                link.rel = "stylesheet"

                root.insertBefore(link, editable)
                field.setAttribute("has-css-injected", "")
            }
        }
    },
}
