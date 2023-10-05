// custom rules for commitlint

module.exports = {
    extends: ['@commitlint/config-conventional'],
    rules: {
        'body-max-line-length': [2, 'always', Infinity],
        'subject-case': [0, 'always', 'lower-case'],
        'body-case': [0, 'always', 'lower-case'],
    },
};
