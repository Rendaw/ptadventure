tup.definerule
{
	inputs={'cairo/generate.py'},
	outputs=
	{
		'icon_col.png',
		'icon_exc.png',
		'icon_inc.png',
		'icon_sort_asc.png',
		'icon_sort_desc.png',
		'icon_sort_rand.png',
		'logo.png',
	},
	command='source env/bin/activate && python ./cairo/generate.py',
}

