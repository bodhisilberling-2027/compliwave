import { useState } from 'react';
import { useUser, useOrganization } from '@clerk/nextjs';
import { Menu, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { UserCircleIcon, BuildingOfficeIcon } from '@heroicons/react/24/outline';
import Link from 'next/link';

export default function Navigation() {
  const { user, signOut } = useUser();
  const { organization, createOrganization } = useOrganization();
  const [isCreatingOrg, setIsCreatingOrg] = useState(false);
  const [orgName, setOrgName] = useState('');

  const handleCreateOrg = async () => {
    if (!orgName) return;
    
    try {
      await createOrganization({ name: orgName });
      setOrgName('');
      setIsCreatingOrg(false);
    } catch (error) {
      console.error('Error creating organization:', error);
    }
  };

  return (
    <nav className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link href="/" className="text-2xl font-bold text-blue-600">
                Compliwave
              </Link>
            </div>
          </div>

          <div className="flex items-center">
            {organization ? (
              <div className="flex items-center space-x-4">
                <div className="flex items-center text-sm text-gray-700">
                  <BuildingOfficeIcon className="h-5 w-5 mr-2" />
                  {organization.name}
                </div>
              </div>
            ) : (
              <button
                onClick={() => setIsCreatingOrg(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Create Organization
              </button>
            )}

            <Menu as="div" className="ml-3 relative">
              <Menu.Button className="flex text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                <UserCircleIcon className="h-8 w-8 text-gray-400" />
              </Menu.Button>

              <Transition
                as={Fragment}
                enter="transition ease-out duration-100"
                enterFrom="transform opacity-0 scale-95"
                enterTo="transform opacity-100 scale-100"
                leave="transition ease-in duration-75"
                leaveFrom="transform opacity-100 scale-100"
                leaveTo="transform opacity-0 scale-95"
              >
                <Menu.Items className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 bg-white ring-1 ring-black ring-opacity-5 focus:outline-none">
                  <Menu.Item>
                    {({ active }) => (
                      <div className="px-4 py-2 text-sm text-gray-700">
                        {user?.emailAddresses[0].emailAddress}
                      </div>
                    )}
                  </Menu.Item>
                  <Menu.Item>
                    {({ active }) => (
                      <button
                        onClick={() => signOut()}
                        className={`${
                          active ? 'bg-gray-100' : ''
                        } block w-full text-left px-4 py-2 text-sm text-gray-700`}
                      >
                        Sign out
                      </button>
                    )}
                  </Menu.Item>
                </Menu.Items>
              </Transition>
            </Menu>
          </div>
        </div>
      </div>

      {/* Organization Creation Modal */}
      {isCreatingOrg && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Create Organization
            </h3>
            <input
              type="text"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              placeholder="Organization name"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <div className="mt-4 flex justify-end space-x-3">
              <button
                onClick={() => setIsCreatingOrg(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateOrg}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
} 