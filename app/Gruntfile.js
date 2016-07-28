module.exports = function (grunt) {
	grunt.initConfig({
		pkg: grunt.file.readJSON('package.json'),
		browserify: {
			dev: {
				files: {
					'static/main.js': ['src/app.jsx']
				},
		        options: {
			        extensions: ['.jsx'],
			        debug: true,
			        transform: [
				        ["babelify", { "presets": ["es2015", "react"] }]
			        ]
		        }
			}
		},
		sass: {
			dist: {
				files: {
					'static/style.css': 'sass/style.scss'
				}
			}
		},
		watch: {
			src: {
				files: ['src/**/*.js', 'src/**/*.jsx'],
				tasks: ['browserify:dev']
			},
			sass: {
				files: ['sass/**/*.scss'],
				tasks: ['sass:dist']
			}
		}
	});

	grunt.loadNpmTasks('grunt-browserify');
	grunt.loadNpmTasks('grunt-contrib-watch');
	grunt.loadNpmTasks('grunt-contrib-sass');

	grunt.registerTask('default', ['browserify', 'sass', 'watch']);
};