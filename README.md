# haru-characters

A shared library of characters for [haru-kit](https://github.com/yungalgo/haru-kit). haru-kit runs [Haru-4B](https://huggingface.co/higurashi-ai/Haru-4B), an open voice model that listens and talks at the same time, on a Mac, an NVIDIA GPU, or a cloud GPU. Haru-4B comes with one example character and no voices, so this is a place to share characters and to try the characters of other people.

A character is a person for Haru to be: a short description (the "card") and a voice, for each language that it speaks.

## Use a character

In haru-kit, click **Browse characters**, then **Add to my library**. On first start, haru-kit adds all the characters of this list to your library.

## Share your character

1. In haru-kit, make your character. Give each language a voice in that language, fill in **Author**, and add a picture (png, jpg or webp, at most 512 KB). A character without a picture is refused.
2. Export it: **Export the character (.haru)**.
3. Here on GitHub, open the folder [`submissions`](submissions), click **Add file → Upload files**, and upload the `.haru` file. GitHub opens a pull request for you.
4. A check comments on your pull request. When the pull request is merged, your character shows in **Browse characters** a minute or two later.

Use your own voice, a public-domain (CC0) voice, or a voice you have permission to share under this repository's license.

To change your character, export it again and upload the new file the same way. It replaces the versions that you wrote.

## Names and languages

- A name belongs to the first person who shares it. If the name is taken, give your character another name.
- You can add a language to someone else's character: add it from **Browse characters**, write the new language version with a voice in that language, export, and upload. You cannot change the languages or voices that other people wrote.

## License

Licensed under the [Apache License 2.0](LICENSE); uploaded characters and voices are shared under the same license. The 9-language cards of `haru` are adapted from [`higurashi-ai/Haru`](https://github.com/higurashi-ai/Haru) (Apache-2.0), and the starter voice clips come from [Mozilla Common Voice 22.0](https://commonvoice.mozilla.org/) (CC0-1.0).
