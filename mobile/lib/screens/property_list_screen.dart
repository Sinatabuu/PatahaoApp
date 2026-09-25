import 'dart:async';

import 'package:flutter/material.dart';

import 'package:mobile/foundation/app_error_message.dart';
import 'package:mobile/models/notification.dart';
import 'package:mobile/models/property.dart';
import 'package:mobile/models/viewing.dart';
import 'package:mobile/screens/customer_notifications_screen.dart';
import 'package:mobile/screens/my_viewings_screen.dart';
import 'package:mobile/screens/property_detail_screen.dart';
import 'package:mobile/screens/viewing_details_screen.dart';
import 'package:mobile/services/notification_service.dart';
import 'package:mobile/services/property_service.dart';
import 'package:mobile/services/favorite_service.dart';
import 'package:mobile/services/deal_service.dart';
import 'package:mobile/services/viewing_service.dart';
import 'package:mobile/widgets/customer_viewing_action_alert.dart';
import '../models/property_type_option.dart';
import '../widgets/pata_hao_network_image.dart';
import 'package:mobile/screens/saved_properties_screen.dart';
import 'package:mobile/screens/customer_profile_screen.dart';
import 'package:mobile/screens/customer_deals_screen.dart';

class PropertyListScreen extends StatefulWidget {
  const PropertyListScreen({super.key, this.onLogout});

  final Future<void> Function()? onLogout;

  @override
  State<PropertyListScreen> createState() => _PropertyListScreenState();
}

class _PropertyListScreenState extends State<PropertyListScreen>
    with WidgetsBindingObserver {
  final PropertyService _propertyService = PropertyService();
  final ViewingService _viewingService = ViewingService();
  final NotificationService _notificationService = const NotificationService();
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  String _selectedListingType = 'all';
  String _selectedPropertyType = 'all';
  int? _selectedBedrooms;
  double? _minimumPrice;
  double? _maximumPrice;
  bool _verifiedOnly = false;
  bool _hasPendingViewingOutcome = false;
  int _unreadNotificationCount = 0;
  bool _isLoadingMore = false;
  bool _hasNextPage = false;
  int _nextPage = 2;
  int _totalPropertyCount = 0;
  int _feedGeneration = 0;
  Timer? _searchDebounce;
  Timer? _customerAlertTimer;
  List<Property> _properties = <Property>[];
  List<Property> _recentSuccesses = <Property>[];
  List<Viewing> _urgentViewingActions = <Viewing>[];
  final Set<String> _shownViewingActionPrompts = <String>{};
  late Future<PropertyFeedPage> _propertiesFuture;
  late Future<List<PropertyTypeOption>> _propertyTypesFuture;

  @override
  void initState() {
    super.initState();

    WidgetsBinding.instance.addObserver(this);
    _loadProperties();
    _loadPropertyTypes();
    _scrollController.addListener(_handleScroll);

    if (widget.onLogout != null) {
      _loadPendingViewingOutcome();
      _loadCustomerAlerts();
      _customerAlertTimer = Timer.periodic(
        const Duration(seconds: 60),
        (_) => _loadCustomerAlerts(),
      );
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _searchDebounce?.cancel();
    _customerAlertTimer?.cancel();
    _scrollController
      ..removeListener(_handleScroll)
      ..dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && widget.onLogout != null) {
      _loadCustomerAlerts();
    }
  }

  void _loadProperties() {
    final generation = ++_feedGeneration;

    _propertiesFuture = _fetchFeedPage(1).then((feed) {
      if (generation == _feedGeneration) {
        _properties = List<Property>.from(feed.properties);
        _recentSuccesses = List<Property>.from(feed.recentSuccesses);
        _totalPropertyCount = feed.count;
        _hasNextPage = feed.hasNext;
        _nextPage = 2;
        _isLoadingMore = false;
      }

      return feed;
    });
  }

  Future<PropertyFeedPage> _fetchFeedPage(int page) {
    return _propertyService.fetchPropertyFeed(
      page: page,
      search: _searchController.text,
      listingType: _selectedListingType,
      propertyType: _selectedPropertyType,
      bedrooms: _selectedBedrooms,
      minimumPrice: _minimumPrice,
      maximumPrice: _maximumPrice,
      verifiedOnly: _verifiedOnly,
    );
  }

  void _loadPropertyTypes() {
    _propertyTypesFuture = _propertyService.fetchPropertyTypes();
  }

  Future<void> _loadPendingViewingOutcome() async {
    try {
      final deals = await DealService.instance.fetchDeals();

      if (!mounted) {
        return;
      }

      final hasPendingOutcome = deals.any(
        (deal) =>
            deal.viewingStatus.toLowerCase() == 'completed' &&
            !deal.customerOutcomeSubmitted,
      );

      setState(() {
        _hasPendingViewingOutcome = hasPendingOutcome;
      });
    } catch (error) {
      debugPrint('PENDING VIEWING OUTCOME ERROR: $error');

      if (!mounted) {
        return;
      }

      setState(() {
        _hasPendingViewingOutcome = false;
      });
    }
  }

  Future<List<Viewing>> _loadViewingsSafely() async {
    try {
      return await _viewingService.getMyViewings();
    } catch (error) {
      debugPrint('CUSTOMER URGENT VIEWINGS ERROR: $error');
      return <Viewing>[];
    }
  }

  Future<List<AppNotification>> _loadNotificationsSafely() async {
    try {
      return await _notificationService.fetchNotifications();
    } catch (error) {
      debugPrint('CUSTOMER NOTIFICATIONS ERROR: $error');
      return <AppNotification>[];
    }
  }

  Future<void> _loadCustomerAlerts({bool showPrompt = true}) async {
    if (widget.onLogout == null) {
      return;
    }

    final results = await Future.wait<dynamic>([
      _loadViewingsSafely(),
      _loadNotificationsSafely(),
    ]);

    if (!mounted) {
      return;
    }

    final viewings = results[0] as List<Viewing>;
    final notifications = results[1] as List<AppNotification>;
    final urgentViewings = viewings
        .where(
          (viewing) =>
              viewing.canRespondToReschedule || viewing.requiresFeeResolution,
        )
        .toList(growable: false);

    setState(() {
      _urgentViewingActions = urgentViewings;
      _unreadNotificationCount = notifications
          .where((notification) => !notification.isRead)
          .length;
    });

    if (showPrompt && urgentViewings.isNotEmpty) {
      _scheduleViewingActionPrompt(urgentViewings.first);
    }
  }

  String _viewingActionPromptKey(Viewing viewing) {
    return <String>[
      viewing.id.toString(),
      viewing.effectiveBookingStatus,
      viewing.proposedDate ?? '',
      viewing.proposedTime ?? '',
      viewing.rescheduleDeclineCount.toString(),
    ].join(':');
  }

  void _scheduleViewingActionPrompt(Viewing viewing) {
    final promptKey = _viewingActionPromptKey(viewing);

    if (!_shownViewingActionPrompts.add(promptKey)) {
      return;
    }

    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) {
        return;
      }

      final shouldReview = await showCustomerViewingActionDialog(
        context,
        viewing: viewing,
      );

      if (shouldReview && mounted) {
        await _openViewingAction(viewing);
      }
    });
  }

  Future<void> _refreshProperties() async {
    setState(_loadProperties);
    await Future.wait<dynamic>([
      _propertiesFuture,
      if (widget.onLogout != null) _loadPendingViewingOutcome(),
      if (widget.onLogout != null) _loadCustomerAlerts(),
    ]);
  }

  void _reloadProperties() {
    setState(_loadProperties);
  }

  void _handleSearchChanged(String _) {
    setState(() {});
    _searchDebounce?.cancel();
    _searchDebounce = Timer(
      const Duration(milliseconds: 400),
      _reloadProperties,
    );
  }

  void _handleScroll() {
    if (!_scrollController.hasClients) {
      return;
    }

    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 500) {
      _loadNextPage();
    }
  }

  Future<void> _loadNextPage() async {
    if (_isLoadingMore || !_hasNextPage) {
      return;
    }

    final generation = _feedGeneration;

    setState(() {
      _isLoadingMore = true;
    });

    try {
      final feed = await _fetchFeedPage(_nextPage);

      if (!mounted || generation != _feedGeneration) {
        return;
      }

      final loadedIds = _properties.map((property) => property.id).toSet();

      setState(() {
        _properties.addAll(
          feed.properties.where((property) => loadedIds.add(property.id)),
        );
        _totalPropertyCount = feed.count;
        _hasNextPage = feed.hasNext;
        _nextPage++;
      });
    } catch (_) {
      if (!mounted || generation != _feedGeneration) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not load more homes. Scroll down to try again.'),
        ),
      );
    } finally {
      if (mounted && generation == _feedGeneration) {
        setState(() {
          _isLoadingMore = false;
        });
      }
    }
  }

  int get _activeFilterCount {
    var count = 0;

    if (_selectedListingType != 'all') {
      count++;
    }
    if (_selectedPropertyType != 'all') {
      count++;
    }
    if (_selectedBedrooms != null) {
      count++;
    }
    if (_minimumPrice != null || _maximumPrice != null) {
      count++;
    }
    if (_verifiedOnly) {
      count++;
    }

    return count;
  }

  void _clearFilters() {
    _searchDebounce?.cancel();

    setState(() {
      _searchController.clear();
      _selectedListingType = 'all';
      _selectedPropertyType = 'all';
      _selectedBedrooms = null;
      _minimumPrice = null;
      _maximumPrice = null;
      _verifiedOnly = false;
      _loadProperties();
    });
  }

  void _openSavedProperties() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const SavedPropertiesScreen()),
    );
  }

  Future<void> _openMyViewings() async {
    await Navigator.of(
      context,
    ).push(MaterialPageRoute<void>(builder: (_) => const MyViewingsScreen()));

    if (!mounted) {
      return;
    }

    await _loadPendingViewingOutcome();
    await _loadCustomerAlerts();
  }

  Future<void> _openViewingAction(Viewing viewing) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ViewingDetailsScreen(viewingId: viewing.id),
      ),
    );

    if (!mounted) {
      return;
    }

    await _loadCustomerAlerts();
  }

  Future<void> _openNotifications() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => const CustomerNotificationsScreen(),
      ),
    );

    if (!mounted) {
      return;
    }

    await _loadCustomerAlerts(showPrompt: false);
  }

  void _openMyDeals() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const CustomerDealsScreen()),
    );
  }

  void _openProfile() {
    if (widget.onLogout == null) {
      return;
    }

    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => CustomerProfileScreen(onLogout: widget.onLogout!),
      ),
    );
  }

  String _formatPrice(Property property) {
    final amount = double.tryParse(property.price);

    final formattedAmount = amount == null
        ? property.price
        : amount
              .toStringAsFixed(0)
              .replaceAllMapped(
                RegExp(r'\B(?=(\d{3})+(?!\d))'),
                (match) => ',',
              );

    if (property.listingType == 'rent') {
      return 'KES $formattedAmount / month';
    }

    return 'KES $formattedAmount';
  }

  String _location(Property property) {
    return [
      property.estate,
      property.town,
      property.county,
    ].where((value) => value.trim().isNotEmpty).join(', ');
  }

  String _mediaUrl(Property property) {
    final media = property.coverMediaUrl?.trim() ?? '';

    if (media.isEmpty) {
      return '';
    }

    if (media.startsWith('http')) {
      return media;
    }

    return '${PropertyService.baseUrl}$media';
  }

  Future<void> _openFilters() async {
    String temporaryListingType = _selectedListingType;
    String temporaryPropertyType = _selectedPropertyType;
    int? temporaryBedrooms = _selectedBedrooms;
    bool temporaryVerifiedOnly = _verifiedOnly;

    final minimumPriceController = TextEditingController(
      text: _minimumPrice?.toStringAsFixed(0) ?? '',
    );

    final maximumPriceController = TextEditingController(
      text: _maximumPrice?.toStringAsFixed(0) ?? '',
    );

    List<PropertyTypeOption> propertyTypes;

    try {
      propertyTypes = await _propertyTypesFuture;
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not load property types. Please try again.'),
        ),
      );

      return;
    }

    if (!mounted) {
      return;
    }

    final shouldApply = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return SafeArea(
              child: Padding(
                padding: EdgeInsets.fromLTRB(
                  20,
                  0,
                  20,
                  20 + MediaQuery.of(context).viewInsets.bottom,
                ),
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Find the right home',
                        style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Choose only what matters to you.',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 24),

                      const Text(
                        'I want to',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 10),

                      SegmentedButton<String>(
                        segments: const [
                          ButtonSegment<String>(
                            value: 'all',
                            label: Text('Any'),
                          ),
                          ButtonSegment<String>(
                            value: 'rent',
                            label: Text('Rent'),
                            icon: Icon(Icons.key_outlined),
                          ),
                          ButtonSegment<String>(
                            value: 'sale',
                            label: Text('Buy'),
                            icon: Icon(Icons.home_outlined),
                          ),
                        ],
                        selected: {temporaryListingType},
                        onSelectionChanged: (selection) {
                          setModalState(() {
                            temporaryListingType = selection.first;
                          });
                        },
                      ),

                      const SizedBox(height: 24),

                      const Text(
                        'Property type',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 10),

                      DropdownButtonFormField<String>(
                        initialValue: temporaryPropertyType,
                        decoration: const InputDecoration(
                          labelText: 'Property type',
                          border: OutlineInputBorder(),
                        ),
                        items: [
                          const DropdownMenuItem<String>(
                            value: 'all',
                            child: Text('Any property type'),
                          ),
                          ...propertyTypes.map(
                            (type) => DropdownMenuItem<String>(
                              value: type.value,
                              child: Text(type.label),
                            ),
                          ),
                        ],
                        onChanged: (String? value) {
                          setModalState(() {
                            temporaryPropertyType = value ?? 'all';

                            if (temporaryPropertyType == 'studio') {
                              temporaryBedrooms = null;
                            }
                          });
                        },
                      ),

                      const SizedBox(height: 24),

                      const Text(
                        'Monthly budget or purchase price',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 10),

                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: minimumPriceController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Minimum',
                                prefixText: 'KES ',
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: TextField(
                              controller: maximumPriceController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Maximum',
                                prefixText: 'KES ',
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 24),

                      const Text(
                        'Bedrooms',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 10),

                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          ChoiceChip(
                            label: const Text('Any'),
                            selected: temporaryBedrooms == null,
                            onSelected: (_) {
                              setModalState(() {
                                temporaryBedrooms = null;
                              });
                            },
                          ),
                          for (final bedrooms in [1, 2, 3, 4])
                            ChoiceChip(
                              label: Text(bedrooms == 4 ? '4+' : '$bedrooms'),
                              selected: temporaryBedrooms == bedrooms,
                              onSelected: (_) {
                                setModalState(() {
                                  temporaryBedrooms = bedrooms;
                                });
                              },
                            ),
                        ],
                      ),

                      const SizedBox(height: 18),

                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        value: temporaryVerifiedOnly,
                        title: const Text('Verified properties only'),
                        subtitle: const Text(
                          'Show listings checked by Pata Hao.',
                        ),
                        secondary: const Icon(
                          Icons.verified_outlined,
                          color: Color(0xFF34AD2C),
                        ),
                        onChanged: (value) {
                          setModalState(() {
                            temporaryVerifiedOnly = value;
                          });
                        },
                      ),

                      const SizedBox(height: 20),

                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: () {
                                setModalState(() {
                                  temporaryListingType = 'all';
                                  temporaryPropertyType = 'all';
                                  temporaryBedrooms = null;
                                  temporaryVerifiedOnly = false;
                                  minimumPriceController.clear();
                                  maximumPriceController.clear();
                                });
                              },
                              child: const Text('Reset'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            flex: 2,
                            child: FilledButton(
                              onPressed: () {
                                Navigator.pop(context, true);
                              },
                              child: const Text('Show Properties'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );

    if (!mounted) {
      minimumPriceController.dispose();
      maximumPriceController.dispose();
      return;
    }

    if (shouldApply == true) {
      setState(() {
        _selectedListingType = temporaryListingType;
        _selectedPropertyType = temporaryPropertyType;
        _selectedBedrooms = temporaryBedrooms;
        _verifiedOnly = temporaryVerifiedOnly;

        _minimumPrice = double.tryParse(
          minimumPriceController.text.replaceAll(',', '').trim(),
        );

        _maximumPrice = double.tryParse(
          maximumPriceController.text.replaceAll(',', '').trim(),
        );

        _loadProperties();
      });
    }

    minimumPriceController.dispose();
    maximumPriceController.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Pata Hao'),
        actions: [
          if (widget.onLogout != null)
            IconButton(
              tooltip: 'Notifications',
              onPressed: _openNotifications,
              icon: Badge(
                isLabelVisible: _unreadNotificationCount > 0,
                label: Text('$_unreadNotificationCount'),
                child: const Icon(Icons.notifications_outlined),
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          if (_urgentViewingActions.isNotEmpty)
            CustomerViewingActionAlert(
              viewing: _urgentViewingActions.first,
              totalActions: _urgentViewingActions.length,
              onReview: () => _openViewingAction(_urgentViewingActions.first),
            ),
          Expanded(
            child: FutureBuilder<PropertyFeedPage>(
              future: _propertiesFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (snapshot.hasError) {
                  return Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.cloud_off, size: 52),
                          const SizedBox(height: 16),
                          const Text(
                            'Could not load properties',
                            style: TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            AppErrorMessage.forError(snapshot.error),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 20),
                          ElevatedButton.icon(
                            onPressed: () {
                              setState(_loadProperties);
                            },
                            icon: const Icon(Icons.refresh),
                            label: const Text('Try Again'),
                          ),
                        ],
                      ),
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: _refreshProperties,
                  child: CustomScrollView(
                    controller: _scrollController,
                    physics: const AlwaysScrollableScrollPhysics(),
                    slivers: [
                      SliverToBoxAdapter(
                        child: _PropertySearchHeader(
                          controller: _searchController,
                          selectedListingType: _selectedListingType,
                          activeFilterCount: _activeFilterCount,
                          resultCount: _totalPropertyCount,
                          onSearchChanged: _handleSearchChanged,
                          onListingTypeChanged: (value) {
                            setState(() {
                              _selectedListingType = value;
                              _loadProperties();
                            });
                          },
                          onOpenFilters: _openFilters,
                          onClearFilters: _clearFilters,
                        ),
                      ),

                      if (_recentSuccesses.isNotEmpty)
                        SliverToBoxAdapter(
                          child: _RecentSuccessStrip(
                            properties: _recentSuccesses,
                          ),
                        ),

                      if (_properties.isEmpty)
                        SliverFillRemaining(
                          hasScrollBody: false,
                          child: _NoMatchingProperties(
                            onClearFilters: _clearFilters,
                          ),
                        ),

                      if (_properties.isNotEmpty)
                        SliverPadding(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                          sliver: SliverList(
                            delegate: SliverChildBuilderDelegate((
                              context,
                              index,
                            ) {
                              final property = _properties[index];

                              return _PropertyCard(
                                property: property,
                                mediaUrl: _mediaUrl(property),
                                location: _location(property),
                                price: _formatPrice(property),
                              );
                            }, childCount: _properties.length),
                          ),
                        ),

                      if (_isLoadingMore)
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: const EdgeInsets.only(bottom: 24),
                            child: Center(
                              child: SizedBox(
                                width: 28,
                                height: 28,
                                child: CircularProgressIndicator(
                                  strokeWidth: 3,
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
      bottomNavigationBar: widget.onLogout == null
          ? null
          : NavigationBar(
              selectedIndex: 0,
              destinations: [
                NavigationDestination(
                  icon: Icon(Icons.home_outlined),
                  selectedIcon: Icon(Icons.home),
                  label: 'Home',
                ),
                NavigationDestination(
                  icon: Icon(Icons.favorite_border),
                  selectedIcon: Icon(Icons.favorite),
                  label: 'Saved',
                ),
                NavigationDestination(
                  icon: Badge(
                    isLabelVisible:
                        _hasPendingViewingOutcome ||
                        _urgentViewingActions.isNotEmpty,
                    child: const Icon(Icons.calendar_month_outlined),
                  ),
                  selectedIcon: Badge(
                    isLabelVisible:
                        _hasPendingViewingOutcome ||
                        _urgentViewingActions.isNotEmpty,
                    child: const Icon(Icons.calendar_month),
                  ),
                  label: 'Viewings',
                ),
                NavigationDestination(
                  icon: Icon(Icons.handshake_outlined),
                  selectedIcon: Icon(Icons.handshake),
                  label: 'Deals',
                ),
                NavigationDestination(
                  icon: Icon(Icons.person_outline),
                  selectedIcon: Icon(Icons.person),
                  label: 'Profile',
                ),
              ],
              onDestinationSelected: (index) {
                switch (index) {
                  case 0:
                    break;

                  case 1:
                    _openSavedProperties();
                    break;

                  case 2:
                    _openMyViewings();
                    break;

                  case 3:
                    _openMyDeals();
                    break;

                  case 4:
                    _openProfile();
                    break;
                }
              },
            ),
    );
  }
}

class _PropertySearchHeader extends StatelessWidget {
  const _PropertySearchHeader({
    required this.controller,
    required this.selectedListingType,
    required this.activeFilterCount,
    required this.resultCount,
    required this.onSearchChanged,
    required this.onListingTypeChanged,
    required this.onOpenFilters,
    required this.onClearFilters,
  });

  final TextEditingController controller;
  final String selectedListingType;
  final int activeFilterCount;
  final int resultCount;
  final ValueChanged<String> onSearchChanged;
  final ValueChanged<String> onListingTypeChanged;
  final VoidCallback onOpenFilters;
  final VoidCallback onClearFilters;

  @override
  Widget build(BuildContext context) {
    final hasSearch = controller.text.trim().isNotEmpty;
    final hasFilters = activeFilterCount > 0 || hasSearch;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Find a place that feels like home',
            style: TextStyle(
              fontSize: 25,
              fontWeight: FontWeight.bold,
              height: 1.2,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Search by area, town, county, or property name.',
            style: TextStyle(
              fontSize: 15,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 18),

          TextField(
            controller: controller,
            onChanged: onSearchChanged,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: 'Try Roysambu, Zimmerman, Kasarani...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: hasSearch
                  ? IconButton(
                      tooltip: 'Clear search',
                      onPressed: () {
                        controller.clear();
                        onSearchChanged('');
                      },
                      icon: const Icon(Icons.close),
                    )
                  : null,
              filled: true,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
                borderSide: BorderSide.none,
              ),
            ),
          ),

          const SizedBox(height: 14),

          Row(
            children: [
              Expanded(
                child: SegmentedButton<String>(
                  segments: const [
                    ButtonSegment<String>(value: 'all', label: Text('All')),
                    ButtonSegment<String>(value: 'rent', label: Text('Rent')),
                    ButtonSegment<String>(value: 'sale', label: Text('Buy')),
                  ],
                  selected: {selectedListingType},
                  onSelectionChanged: (selection) {
                    onListingTypeChanged(selection.first);
                  },
                ),
              ),
              const SizedBox(width: 10),
              Badge(
                isLabelVisible: activeFilterCount > 0,
                label: Text('$activeFilterCount'),
                child: IconButton.filledTonal(
                  tooltip: 'More filters',

                  onPressed: onOpenFilters,
                  icon: const Icon(Icons.tune),
                ),
              ),
            ],
          ),

          const SizedBox(height: 18),

          Row(
            children: [
              Expanded(
                child: Text(
                  resultCount == 1
                      ? '1 home found'
                      : '$resultCount homes found',
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              if (hasFilters)
                TextButton(
                  onPressed: onClearFilters,
                  child: const Text('Clear all'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RecentSuccessStrip extends StatelessWidget {
  const _RecentSuccessStrip({required this.properties});

  final List<Property> properties;

  String _mediaUrl(Property property) {
    final media = property.coverMediaUrl?.trim() ?? '';

    if (media.isEmpty || media.startsWith('http')) {
      return media;
    }

    return '${PropertyService.baseUrl}$media';
  }

  String _location(Property property) {
    return [
      property.estate,
      property.town,
    ].where((value) => value.trim().isNotEmpty).join(', ');
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 0, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.verified_outlined, size: 18, color: Color(0xFFD97706)),
              SizedBox(width: 7),
              Expanded(
                child: Text(
                  'Recently completed through Pata Hao',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF78350F),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 9),
          SizedBox(
            height: 112,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: properties.length,
              padding: const EdgeInsets.only(right: 16),
              separatorBuilder: (_, _) => const SizedBox(width: 10),
              itemBuilder: (context, index) {
                final property = properties[index];
                final isSold = property.status.trim().toLowerCase() == 'sold';

                return SizedBox(
                  width: 232,
                  child: Card(
                    margin: EdgeInsets.zero,
                    elevation: 0,
                    clipBehavior: Clip.antiAlias,
                    shape: RoundedRectangleBorder(
                      side: const BorderSide(color: Color(0xFFFDE68A)),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: InkWell(
                      onTap: () {
                        Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) =>
                                PropertyDetailScreen(property: property),
                          ),
                        );
                      },
                      child: Row(
                        children: [
                          PataHaoNetworkImage(
                            imageUrl: _mediaUrl(property).isEmpty
                                ? null
                                : _mediaUrl(property),
                            width: 88,
                            height: 112,
                            fit: BoxFit.cover,
                            cacheWidth: 360,
                          ),
                          Expanded(
                            child: Padding(
                              padding: const EdgeInsets.all(10),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 7,
                                      vertical: 3,
                                    ),
                                    decoration: BoxDecoration(
                                      color: isSold
                                          ? const Color(0xFFFEE2E2)
                                          : const Color(0xFFFEF3C7),
                                      borderRadius: BorderRadius.circular(20),
                                    ),
                                    child: Text(
                                      isSold ? 'SOLD' : 'RENTED',
                                      style: TextStyle(
                                        color: isSold
                                            ? const Color(0xFF991B1B)
                                            : const Color(0xFF92400E),
                                        fontSize: 10,
                                        fontWeight: FontWeight.w800,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 7),
                                  Text(
                                    property.title,
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w700,
                                      height: 1.15,
                                    ),
                                  ),
                                  const Spacer(),
                                  Text(
                                    _location(property),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontSize: 11,
                                      color: Colors.black54,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _NoMatchingProperties extends StatelessWidget {
  const _NoMatchingProperties({required this.onClearFilters});

  final VoidCallback onClearFilters;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.search_off_outlined,
              size: 68,
              color: Color(0xFF34AD2C),
            ),
            const SizedBox(height: 18),
            const Text(
              'No homes match your search',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Try another location, increase your budget, '
              'or remove one of the filters.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: onClearFilters,
              icon: const Icon(Icons.refresh),
              label: const Text('See all properties'),
            ),
          ],
        ),
      ),
    );
  }
}

class _PropertyCard extends StatefulWidget {
  const _PropertyCard({
    required this.property,
    required this.mediaUrl,
    required this.location,
    required this.price,
  });

  final Property property;
  final String mediaUrl;
  final String location;
  final String price;

  @override
  State<_PropertyCard> createState() => _PropertyCardState();
}

class _PropertyCardState extends State<_PropertyCard> {
  late Property _property;
  bool _isUpdatingFavorite = false;

  @override
  void initState() {
    super.initState();
    _property = widget.property;
  }

  @override
  void didUpdateWidget(covariant _PropertyCard oldWidget) {
    super.didUpdateWidget(oldWidget);

    if (oldWidget.property.id != widget.property.id ||
        oldWidget.property.status != widget.property.status ||
        oldWidget.property.isSuccessBroadcastActive !=
            widget.property.isSuccessBroadcastActive ||
        oldWidget.property.successBadge != widget.property.successBadge ||
        oldWidget.property.isFavorite != widget.property.isFavorite ||
        oldWidget.property.favoriteId != widget.property.favoriteId) {
      _property = widget.property;
    }
  }

  Future<void> _toggleFavorite() async {
    if (_isUpdatingFavorite) {
      return;
    }

    final previousProperty = _property;
    final wasFavorite = previousProperty.isFavorite;
    final favoriteId = previousProperty.favoriteId;

    if (wasFavorite && favoriteId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'This saved property is missing its favorite reference. '
            'Refresh the property list and try again.',
          ),
        ),
      );
      return;
    }

    setState(() {
      _isUpdatingFavorite = true;
      _property = previousProperty.copyWith(
        isFavorite: !wasFavorite,
        clearFavoriteId: wasFavorite,
      );
    });

    try {
      if (wasFavorite) {
        await FavoriteService.instance.removeFavorite(favoriteId: favoriteId!);
      } else {
        final favorite = await FavoriteService.instance.saveProperty(
          propertyId: previousProperty.id,
        );

        if (!mounted) {
          return;
        }

        setState(() {
          _property = _property.copyWith(
            isFavorite: true,
            favoriteId: favorite.id,
          );
        });
      }

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            wasFavorite ? 'Removed from saved properties.' : 'Property saved.',
          ),
          duration: const Duration(seconds: 2),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _property = previousProperty;
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(AppErrorMessage.forError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isUpdatingFavorite = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 20),
      clipBehavior: Clip.antiAlias,
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: InkWell(
        onTap: () async {
          await Navigator.push(
            context,
            MaterialPageRoute<void>(
              builder: (_) => PropertyDetailScreen(property: _property),
            ),
          );

          if (!mounted) {
            return;
          }

          // Reload so changes made on the details screen are reflected here.
          // This remains harmless until the details-screen heart is connected.
        },
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Stack(
              children: [
                SizedBox(
                  height: 220,
                  width: double.infinity,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      PataHaoNetworkImage(
                        imageUrl: widget.mediaUrl.isEmpty
                            ? null
                            : widget.mediaUrl,
                        width: double.infinity,
                        height: 220,
                        fit: BoxFit.cover,
                        cacheWidth: 900,
                      ),
                      if (_property.hasVideo)
                        const Center(
                          child: CircleAvatar(
                            radius: 30,
                            backgroundColor: Colors.black54,
                            child: Icon(
                              Icons.play_arrow_rounded,
                              size: 42,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      if (_property.hasVideo)
                        Positioned(
                          left: 12,
                          bottom: 12,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.black54,
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: const Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.videocam_rounded,
                                  size: 16,
                                  color: Colors.white,
                                ),
                                SizedBox(width: 5),
                                Text(
                                  'Video',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                Positioned(
                  top: 12,
                  left: 12,
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 215),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 7,
                      ),
                      decoration: BoxDecoration(
                        color: _property.isSuccessBroadcastActive
                            ? (_property.status.trim().toLowerCase() == 'sold'
                                  ? const Color(0xFFB91C1C)
                                  : const Color(0xFFD97706))
                            : const Color(0xFF34AD2C),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (_property.isSuccessBroadcastActive) ...[
                            Icon(
                              _property.status.trim().toLowerCase() == 'sold'
                                  ? Icons.sell_outlined
                                  : Icons.key_outlined,
                              size: 15,
                              color: Colors.white,
                            ),
                            const SizedBox(width: 5),
                          ],
                          Flexible(
                            child: Text(
                              _property.isSuccessBroadcastActive
                                  ? _property.successDisplayLabel.toUpperCase()
                                  : (_property.listingType == 'rent'
                                        ? 'For Rent'
                                        : 'For Sale'),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                Positioned(
                  top: 12,
                  right: 12,
                  child: CircleAvatar(
                    backgroundColor: Colors.white,
                    child: _isUpdatingFavorite
                        ? const Padding(
                            padding: EdgeInsets.all(12),
                            child: SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                          )
                        : IconButton(
                            tooltip: _property.isFavorite
                                ? 'Remove from saved properties'
                                : 'Save property',
                            icon: Icon(
                              _property.isFavorite
                                  ? Icons.favorite
                                  : Icons.favorite_border,
                              color: _property.isFavorite
                                  ? Colors.red
                                  : const Color(0xFF34AD2C),
                            ),
                            onPressed: _toggleFavorite,
                          ),
                  ),
                ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          _property.title,
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      if (_property.trustBadge != 'none')
                        const Icon(Icons.verified, color: Color(0xFF34AD2C)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Icon(
                        Icons.location_on_outlined,
                        size: 18,
                        color: Colors.black54,
                      ),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          widget.location,
                          style: const TextStyle(color: Colors.black54),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      const Icon(Icons.bed_outlined, size: 20),
                      const SizedBox(width: 5),
                      Text('${_property.bedrooms} beds'),
                      const SizedBox(width: 20),
                      const Icon(Icons.bathtub_outlined, size: 20),
                      const SizedBox(width: 5),
                      Text('${_property.bathrooms} baths'),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    widget.price,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF34AD2C),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
